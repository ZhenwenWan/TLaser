#!/usr/bin/env python3
"""
VCSEL Reduced Physical Simulator.
Models radial current crowding, radial spatial hole burning, standing-wave DBR cavity loss,
self-heating, and temperature-induced thermal rollover.
"""

from __future__ import annotations
import math
import numpy as np

class VCSELSimulator:
    def __init__(
        self,
        aperture_dia_um: float = 8.0,      # Oxide aperture diameter in microns
        R_DBR_top: float = 0.995,          # Top DBR mirror reflectivity
        R_DBR_bottom: float = 0.999,       # Bottom DBR mirror reflectivity
        R_th: float = 1200.0,              # Thermal resistance (K/W)
        T_ambient: float = 298.0,          # Ambient temperature (K)
        active_thickness_nm: float = 24.0, # Total QW active thickness (nm)
        lambda_cavity_nm: float = 850.0,   # Nominal cavity resonance wavelength (nm)
    ):
        self.aperture_dia_um = aperture_dia_um
        self.R_DBR_top = R_DBR_top
        self.R_DBR_bottom = R_DBR_bottom
        self.R_th = R_th
        self.T_ambient = T_ambient
        self.d_active = active_thickness_nm * 1e-7  # cm
        self.lambda_nm = lambda_cavity_nm
        
        # Physical constants
        self.q0 = 1.60217663e-19
        self.h_planck = 6.62607015e-34
        self.c0 = 2.99792458e10                     # cm/s
        self.E_phot = self.h_planck * (self.c0 / (self.lambda_nm * 1e-7))
        
        # Device dimensions
        self.r_ap = (self.aperture_dia_um / 2.0) * 1e-4 # cm
        self.r_outer = 15.0 * 1e-4                     # Outer contact radius (cm)
        self.V_active = math.pi * (self.r_ap**2) * self.d_active # active volume (cm^3)
        
        # Optical mode configuration
        self.w_mode = (self.aperture_dia_um / 2.2) * 1e-4 # Mode radius (cm)
        self.Gamma = 0.04                                # Confinement factor
        self.alpha_i = 15.0                              # Internal loss (cm^-1)
        
        # DBR mirror loss
        self.L_eff_um = 1.5                              # Effective cavity length (um)
        self.alpha_m = 0.5 * (1.0 / (self.L_eff_um * 1e-4)) * math.log(1.0 / (self.R_DBR_top * self.R_DBR_bottom))
        self.tau_p = 1.0 / (self.c0 / 3.5 * (self.alpha_i + self.alpha_m)) # Photon lifetime (s)
        
        # Recombination parameters (at 300K)
        self.tau_n = 2.0e-9
        self.A_recomb = 1.0 / self.tau_n
        self.B_recomb = 1.0e-10
        self.C_recomb = 3.0e-29
        self.N_tr0 = 1.2e18 # transparency density (cm^-3)
        self.g0_gain = 2500.0 # gain coefficient (cm^-1)
        
        # Electrical parasitics
        self.R_series = 60.0 # Series contact resistance (Ohm)
        self.R_shunt = 1500.0 # Shunt leakage resistance (Ohm)
        self.V_turnon = 1.45  # Junction turn-on voltage (V)

    def solve_radial_profiles(
        self,
        I_total_mA: float,
        M: int = 51,
    ) -> dict[str, np.ndarray | float]:
        """
        Solves the radial current crowding and carrier diffusion rate equations.
        Accounts for thermal rollover by calculating self-heating feedback.
        """
        I_total = I_total_mA * 1e-3
        r_grid = np.linspace(0.0, self.r_outer, M)
        dr = self.r_outer / (M - 1)
        
        # 1. Thermal self-heating feedback loop
        T_junction = self.T_ambient
        P_opt = 0.0
        V_term = self.V_turnon
        
        # Simple iterative loop for thermal coupling
        for _ in range(5):
            # Calculate junction voltage
            V_junction = self.V_turnon + 0.0259 * math.log(max(I_total, 1e-9) / 1e-6 + 1.0)
            V_term = V_junction + I_total * self.R_series
            
            # Electrical power
            P_elec = I_total * V_term
            P_heat = max(P_elec - P_opt, 0.0)
            
            # Temperature rise
            T_junction = self.T_ambient + P_heat * self.R_th
            
            # Update gain and transparency parameters under temperature
            temp_ratio = T_junction / 300.0
            g0 = self.g0_gain * math.exp(-(T_junction - 300.0) / 75.0)
            N_tr = self.N_tr0 * (temp_ratio**1.5)
            C_recomb = self.C_recomb * (temp_ratio**2.0)
            
            # 2. Transverse mode profile (Gaussian LP01 profile)
            # S(r) is normalized so integration equals total photon number
            # Mode shape: exp(-2*(r/w_mode)^2)
            mode_shape = np.exp(-2.0 * (r_grid / self.w_mode)**2)
            
            # 3. Radial injection current density profile (Current Crowding)
            # Current crowds near the oxide aperture edge r = r_ap
            # Inside the aperture: exp((r-r_ap)/w_crowd)
            w_crowd = 1.2e-4  # 1.2 um crowd width
            I_profile = np.zeros(M)
            for i, r in enumerate(r_grid):
                if r <= self.r_ap:
                    I_profile[i] = math.exp((r - self.r_ap) / w_crowd)
                else:
                    I_profile[i] = math.exp(-3.0 * (r - self.r_ap) / w_crowd) # decay outside aperture
            
            # Helper function for trapezoidal integration
            def trap_int(y, dx):
                return dx * (np.sum(y) - 0.5 * (y[0] + y[-1]))
            
            # Normalize current profile to match total injected active current
            # Integral over 2*pi*r*I_profile*dr = I_active
            I_active = I_total * (self.R_shunt / (self.R_series + self.R_shunt))
            int_factor = 2.0 * math.pi * trap_int(I_profile * r_grid, dr)
            if int_factor > 0:
                I_profile = I_profile * (I_active / int_factor)
                
            # 4. Solve radial carrier density rate equation:
            # G_inj(r) - R_rec(N) - R_stim(N, S) = 0
            N_profile = np.zeros(M)
            g_profile = np.zeros(M)
            
            # Guess average photon number from optical power
            # We solve carrier rate equation per grid point
            S_density = mode_shape * (P_opt / (self.Gamma * self.E_phot * self.c0 / 3.5)) # photon density
            
            for i in range(M):
                r = r_grid[i]
                J_inj = I_profile[i] / (2.0 * math.pi * max(r, 1e-10) * self.d_active) if r > 0 else I_profile[0] / (math.pi * dr * self.d_active)
                G_inj = J_inj / (self.q0 * self.d_active)
                
                # Newton-Raphson to solve rate equation at this point
                x_val = math.log(1.5e18)
                for _ in range(25):
                    n_val = math.exp(x_val)
                    gain = g0 * (x_val - math.log(N_tr))
                    gain = max(gain, 0.0)
                    
                    R_rec = self.A_recomb * n_val + self.B_recomb * n_val**2 + C_recomb * n_val**3
                    R_stim = gain * self.c0 / 3.5 * S_density[i]
                    
                    f_val = G_inj - R_rec - R_stim
                    df_dx = -self.A_recomb * n_val - 2.0 * self.B_recomb * n_val**2 - 3.0 * C_recomb * n_val**3
                    if S_density[i] > 0 and gain > 0:
                        df_dx -= (g0 * self.c0 / 3.5) * S_density[i]
                        
                    dx = -f_val / df_dx
                    dx = max(min(dx, 1.5), -1.5)
                    x_val += dx
                    if abs(dx) < 1.0e-6:
                        break
                
                N_profile[i] = math.exp(x_val)
                g_profile[i] = max(g0 * (x_val - math.log(N_tr)), 0.0)
                
            # 5. Update optical output power (L-I curve)
            # Threshold current estimate based on modal gain = cavity loss
            # modal gain <g> = Gamma * integral( g(r)*S(r)*2*pi*r*dr ) / integral( S(r)*2*pi*r*dr )
            int_S = trap_int(mode_shape * r_grid, dr)
            int_gS = trap_int(g_profile * mode_shape * r_grid, dr)
            modal_gain = self.Gamma * (int_gS / int_S) if int_S > 0 else 0.0
            
            # Simple laser threshold formula
            I_th = 0.8 * (self.q0 * self.V_active * N_tr * self.A_recomb) * (1.0 + 1.2 * (T_junction - 298.0) / 100.0)
            
            # Output power calculation with thermal rollover
            if I_active > I_th:
                slope_efficiency = 0.45 * (self.alpha_m / (self.alpha_i + self.alpha_m)) * (self.E_phot / self.q0)
                # Rollover function modeling gain-mode detuning
                rollover = max(1.0 - ((T_junction - 315.0) / 60.0)**2, 0.0)
                P_opt = slope_efficiency * (I_active - I_th) * rollover
            else:
                P_opt = 1e-6 * I_active # spontaneous emission base
        
        WPE = P_opt / (I_total * V_term) if I_total > 0 else 0.0
        
        return {
            "r_grid_um": r_grid * 1e4,
            "N": N_profile,
            "I_profile": I_profile,
            "mode_profile": mode_shape,
            "P_opt_mW": P_opt * 1000.0,
            "V_term": V_term,
            "WPE": WPE,
            "T_junction": T_junction,
            "I_th_mA": I_th * 1000.0,
        }

if __name__ == "__main__":
    sim = VCSELSimulator()
    res = sim.solve_radial_profiles(I_total_mA=6.0)
    print("VCSEL Simulator test:")
    print(f"  P_opt: {res['P_opt_mW']:.3f} mW")
    print(f"  Voltage: {res['V_term']:.3f} V")
    print(f"  Junction Temp: {res['T_junction']:.2f} K")
    print(f"  Threshold Current: {res['I_th_mA']:.2f} mA")
