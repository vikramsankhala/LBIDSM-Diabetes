import io
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scripts.external_cgmacros import choose_t2dm, harmonize

def test_t2dm_hba1c_selection():
    bio=pd.DataFrame({"ID":[1,2,3],"A1c PDL (Lab)":[5.5,6.1,7.2]})
    ids,rule=choose_t2dm(bio)
    assert ids=={3}
    assert "proxy" in rule

def test_unknown_phenotype_fails_closed():
    with pytest.raises(ValueError):
        choose_t2dm(pd.DataFrame({"ID":[1],"group":["unknown"]}))

def test_mock_zip_harmonization(tmp_path):
    path=tmp_path/"mock.zip"
    bio=pd.DataFrame({"ID":[1,2],"A1c PDL (Lab)":[7.2,5.5]})
    ts=pd.date_range("2026-01-01",periods=90,freq="min")
    cg=pd.DataFrame({"Timestamp":ts.astype(str),"Dexcom GL":np.linspace(110,120,90)})
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("bio.csv",bio.to_csv(index=False))
        z.writestr("CGMacros-001/CGMacros-001.csv",cg.to_csv(index=False))
    d,meta=harmonize(path)
    assert d.subject_id.nunique()==1
    assert len(d)==18
