"""Numerical field checks and CAE job/model trust boundaries."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from cae_fields import potential_gradient, available_fields, read_vtu
from cae_jobs import write_json, check_cancel, job_path
from cae_training import ValidatedSurrogate, evaluate


class CAETests(unittest.TestCase):
    def test_linear_potential_gradient_and_em_phase(self):
        points = np.array([[0.,0,0],[2,0,0],[0,3,0],[2,3,0]])
        triangles = np.array([[0,1,2],[1,3,2]])
        potential = 2*points[:,0]-3*points[:,1]+4
        np.testing.assert_allclose(potential_gradient(points,triangles,potential), [[-2,3]]*4)
        raw = {"carriers":np.column_stack((potential,np.ones(4)*1e18,np.ones(4)*2e18)),
               "electric field re":np.ones((4,3)), "electric field im":np.ones((4,3))*2,
               "temperature":np.ones(4)*300}
        fields = available_fields(points,triangles,raw,np.pi/2)
        np.testing.assert_allclose(fields["electric field phase [3] (solver units)"],-2)
        np.testing.assert_allclose(fields["Electrostatic |E| (V/cm), derived"],np.sqrt(13))

    def test_ascii_vtu_and_degenerate_mesh(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"field.vtu"
            path.write_text('''<VTKFile type="UnstructuredGrid"><UnstructuredGrid><Piece>
            <Points><DataArray type="Float64" NumberOfComponents="3">0 0 0 1 0 0 0 1 0</DataArray></Points>
            <Cells><DataArray type="Int32" Name="connectivity">0 1 2</DataArray>
            <DataArray type="Int32" Name="offsets">3</DataArray>
            <DataArray type="UInt8" Name="types">5</DataArray></Cells>
            <PointData><DataArray type="Float64" Name="Temperature">300 301 302</DataArray></PointData>
            </Piece></UnstructuredGrid></VTKFile>''')
            points,triangles,fields=read_vtu(path)
            self.assertEqual(triangles.tolist(),[[0,1,2]])
            self.assertEqual(fields["temperature"].tolist(),[300,301,302])
            with self.assertRaises(ValueError):
                potential_gradient(points, np.array([[0,0,1]]), np.ones(3))

    def test_atomic_write_retries_windows_sharing_violation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"progress.json"
            original=Path.replace
            calls=[]
            def replace(source,target):
                calls.append(1)
                if len(calls)==1:
                    raise PermissionError("Windows sharing violation")
                return original(source,target)
            with patch.object(Path,"replace",replace):
                write_json(path,{"done":3})
            self.assertEqual(json.loads(path.read_text()),{"done":3})
            self.assertEqual(len(calls),2)
            (Path(directory)/"cancel").touch()
            with self.assertRaises(InterruptedError):
                check_cancel(Path(directory))
        with self.assertRaises(ValueError):
            job_path("../outside")

    def test_reject_unvalidated_or_modified_model(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            write_json(folder/"evaluation.json",{"eligible":False})
            with self.assertRaisesRegex(ValueError,"validation"):
                ValidatedSurrogate(folder)
            (folder/"model").mkdir()
            (folder/"model/pinn_laser_model.pt").write_bytes(b"changed")
            write_json(folder/"evaluation.json",{"eligible":True,"checkpoint_sha256":"bad"})
            with self.assertRaisesRegex(ValueError,"checksum"):
                ValidatedSurrogate(folder)

    def test_prediction_rejects_extrapolation(self):
        from cae_training import KEYS,PREDICT_KEYS
        model=object.__new__(ValidatedSurrogate)
        model.ranges={key:[0.,1.] for key in KEYS}
        with self.assertRaisesRegex(ValueError,"outside"):
            model.predict(**{key:2. for key in PREDICT_KEYS})


if __name__ == "__main__":
    unittest.main()
