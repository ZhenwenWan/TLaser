#!/usr/bin/env python3
"""
Quasi-3D Laser Simulator Synthesizer.
Solves the 1D longitudinal optical propagation and carrier rate equations (SHB)
coupled with baseline 2D transverse parameters from Elmer.
"""

from __future__ import annotations
import math
import numpy as np

class Quasi3DSimulator:
    def __init__(
        self,
        L_cavity: float = 300.0e-4,  # cm
        R1: float = 0.3,
        R2: float = 0.3,
        M: int = 51,
        alpha_i: float = 10.0,       # cm^-1
        w_active: float = 2.8e-4,    # cm
        d_active: float = 0.1e-4,    # cm
        n_g: float = 3.6,
        n_r: float = 3.35,
        T0: float = 300.0,           # K
    ):
        self.L_cavity = L_cavity
        self.R1 = R1
        self.R2 = R2
        self.M = M
        self.alpha_i = alpha_i
        self.w_active = w_active
        self.d_active = d_active
        self.n_g = n_g
        self.n_r = n_r
        self.T0 = T0
        
        # Confinement factor
        self.Gamma = 0.05
        
        # Default electrical parasitics for WPE calculations
        self.R_shunt = 150.0        # Ohm
        self.R_series = 0.85       # Ohm
        
        # Constants
        self.q0 = 1.60213377e-19
        self.c0 = 2.99792458e10      # cm/s
        self.v_g = self.c0 / self.n_r
        self.h_planck = 6.62607015e-34
        
        # Temperature physical scaling laws (InGaAsP baseline at 300 K)
        temp_gain_scale = math.exp(-(T0 - 300.0) / 120.0)
        temp_ntr_scale = (T0 / 300.0)**1.5
        temp_auger_scale = (T0 / 300.0)**2.0
        
        self.tau = 1.0e-8
        self.A_recomb = 1.0 / self.tau
        self.B_recomb = 1.0e-10
        self.C_recomb = 3.0e-29 * temp_auger_scale
        self.N_tr = 1.0e18 * temp_ntr_scale
        self.g0_gain = 1200.0 * temp_gain_scale
        
        # Spontaneous coupling factor
        self.beta_sp = 1.0e-4

    def solve_longitudinal(
        self,
        I_2d_unit: float,            # Current per unit length (A/cm)
        freq: float = 1.934e14,      # Hz
        verbose: bool = False,
    ) -> dict[str, np.ndarray | float]:
        """
        Solves the coupled 1D photon propagation and carrier equations along z.
        Uses a shooting method to satisfy mirror boundary conditions.
        """
        dz = self.L_cavity / (self.M - 1)
        z_grid = np.linspace(0, self.L_cavity, self.M)
        
        # Local photon energy
        E_phot = self.h_planck * freq
        
        # Area of active region cross section
        A_act = self.w_active * self.d_active
        
        # We guess P_plus(0) at the left boundary.
        # Boundary condition: P_minus(0) = P_plus(0) / R1
        # Bisection search range
        p_guess_min = 1.0e-6
        p_guess_max = 50.0   # 50 Watts
        
        P_plus = np.zeros(self.M)
        P_minus = np.zeros(self.M)
        N = np.zeros(self.M)
        g = np.zeros(self.M)
        
        def propagate(p_plus_0: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
            p_p = np.zeros(self.M)
            p_m = np.zeros(self.M)
            n_arr = np.zeros(self.M)
            g_arr = np.zeros(self.M)
            
            p_p[0] = p_plus_0
            p_m[0] = p_plus_0 / self.R1
            
            # Step along z
            for k in range(self.M):
                P_tot = p_p[k] + p_m[k]
                
                # Carrier rate equation solver (Stable Log-Newton method)
                x_val = math.log(1.5e18)
                G_inj = I_2d_unit / (self.q0 * A_act)
                
                for _ in range(30):
                    n_val = math.exp(x_val)
                    gain = self.g0_gain * (x_val - math.log(self.N_tr))
                    gain = max(gain, 0.0) # non-negative gain clamping
                    
                    R_rec = self.A_recomb * n_val + self.B_recomb * n_val**2 + self.C_recomb * n_val**3
                    R_stim = (gain * P_tot) / (A_act * E_phot) if P_tot > 0 else 0.0
                    
                    f_val = G_inj - R_rec - R_stim
                    
                    # df/dx
                    df_dx = -self.A_recomb * n_val - 2.0 * self.B_recomb * n_val**2 - 3.0 * self.C_recomb * n_val**3
                    if P_tot > 0 and gain > 0:
                        df_dx -= (self.g0_gain * P_tot) / (A_act * E_phot)
                        
                    dx = -f_val / df_dx
                    # Clamp step size to prevent overflow
                    dx = max(min(dx, 2.0), -2.0)
                    x_val += dx
                    if abs(dx) < 1.0e-8:
                        break
                
                n_val = math.exp(x_val)
                n_arr[k] = n_val
                g_arr[k] = self.g0_gain * (x_val - math.log(self.N_tr))
                g_arr[k] = max(g_arr[k], 0.0)
                
                # 2. Integrate to next segment (Euler integration)
                if k < self.M - 1:
                    R_sp = self.B_recomb * n_val**2
                    net_gain_p = (self.Gamma * g_arr[k] - self.alpha_i) * p_p[k] + self.beta_sp * R_sp * A_act * E_phot
                    net_gain_m = (self.Gamma * g_arr[k] - self.alpha_i) * p_m[k] + self.beta_sp * R_sp * A_act * E_phot
                    
                    p_p[k+1] = p_p[k] + net_gain_p * dz
                    p_m[k+1] = p_m[k] - net_gain_m * dz
                    
                    p_p[k+1] = max(p_p[k+1], 1.0e-12)
                    p_m[k+1] = max(p_m[k+1], 1.0e-12)
            
            return p_p, p_m, n_arr, g_arr
            
        # Bisection loop
        for itr in range(50):
            p_guess = 0.5 * (p_guess_min + p_guess_max)
            p_p, p_m, n_arr, g_arr = propagate(p_guess)
            
            # Boundary condition at z=L: P_minus(L) = R2 * P_plus(L)
            residual = p_m[-1] - self.R2 * p_p[-1]
            
            if abs(residual) < 1.0e-6 * (p_p[-1] + 1.0e-6):
                break
                
            if residual > 0:
                # Too much power in p_m at L, decrease guess
                p_guess_max = p_guess
            else:
                p_guess_min = p_guess
                
        P_plus, P_minus, N, g = p_p, p_m, n_arr, g_arr
        
        # Calculate WPE and optical power
        # Output power from both facets
        P_out_facet1 = P_minus[0] * (1.0 - self.R1)
        P_out_facet2 = P_plus[-1] * (1.0 - self.R2)
        P_opt = P_out_facet1 + P_out_facet2
        
        I_active = I_2d_unit * self.L_cavity
        # Electrical junction voltage based on active current (same as calibration)
        V_junction = 0.95 + 0.05 * math.log(max(I_active, 1e-9) / 1e-6 + 1.0)
        I_shunt = V_junction / self.R_shunt
        I_total = I_active + I_shunt
        
        # Terminal voltage and electrical power
        V_bias = V_junction + I_total * self.R_series
        P_elec = I_total * V_bias
        wpe = P_opt / P_elec if P_elec > 0 else 0.0
        
        if verbose:
            print(f"Quasi-3D converged in {itr+1} shooting iterations.")
            print(f"  P_opt (W): {P_opt:.4f}")
            print(f"  I_total (A): {I_total:.4f}")
            print(f"  WPE (%): {wpe*100.0:.4f}")
            
        return {
            "z_grid": z_grid,
            "P_plus": P_plus,
            "P_minus": P_minus,
            "N": N,
            "g": g,
            "P_opt": P_opt,
            "P_elec": P_elec,
            "I_total": I_total,
            "WPE": wpe,
        }
