import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest

from womi.adapters import control, depth_export, predict
from womi.contracts import dataset, target_arrays
from womi.demo import generate
from womi.evaluate import compare, evaluate, measure, replay
from womi.io import InvalidEvidence, digest, file_hash, load_arrays, read_json, safe_file
from womi.metrics import interval, score


@pytest.fixture
def run(tmp_path):
    manifest, targets = generate(tmp_path/"data", worlds=2)
    submission = predict(manifest, tmp_path/"predictions", adapter="last-frame", name="Copy", revision="test", kind="control")
    return manifest, targets, submission


def rewrite(path, doc):
    path.write_text(json.dumps(doc, allow_nan=False))


def changed_array(index_path, case_id, root, arrays):
    index = read_json(index_path)
    row = index["cases"][case_id]
    reference = row["output"] if "output" in row else row
    path = root/reference["path"]
    np.savez_compressed(path, **arrays)
    reference["sha256"] = file_hash(path)
    rewrite(index_path, index)


def test_complete_run_and_replay(run, tmp_path):
    report = evaluate(*run, tmp_path/"report")
    assert report["measurements"]["assigned"] == 10
    assert report["measurements"]["successful"] == 10
    assert report["scope"] == "synthetic_diagnostic"
    assert report["cross_track_aggregate"] is None
    assert report["measurements"]["total_cost_usd"] is None
    assert replay(*run, tmp_path/"report/report.json")["recomputed"]
    assert len(list((tmp_path/"report/previews").glob("*.png"))) == 5


def test_perfect_predictions_and_metric_ceiling(run):
    m, t, s = run
    targets = read_json(t)
    for case_id, row in targets["cases"].items():
        arrays = load_arrays(t.parent/row["path"])
        output = {k: v for k, v in arrays.items() if k in ("rgb", "depth")}
        changed_array(s, case_id, s.parent, output)
    report = measure(*run)
    for row in report["measurements"]["cases"]:
        for key, value in row["metrics"].items():
            assert value == (60.0 if key == "rgb_psnr_capped_db" else 0.0)


def test_depth_uses_z_meters_without_scale_fitting():
    t = {"depth": np.array([[[2., 4.]]]), "valid": np.ones((1,1,2), bool)}
    result = score({"task":"geometry"}, {"depth": np.array([[[4., 6.]]])}, t)
    assert result["depth_relative_error_bounded"] == .75
    result = score({"task":"geometry"}, {"depth": np.array([[[0., -1.]]])}, t)
    assert result["depth_relative_error_bounded"] == 1


def test_edit_preservation_not_hidden_by_small_roi():
    target = {"rgb": np.zeros((1,1,2,3),np.uint8), "valid":np.ones((1,1,2),bool),
              "region":np.array([[[True,False]]])}
    p = np.zeros((1,1,2,3),np.uint8); p[0,0,1] = 255
    result = score({"task":"editing"},{"rgb":p},target)
    assert result == {"edit_region_mae":0., "preserved_region_mae":1.}


def test_foreground_prevents_static_background_dominating():
    rgb=np.zeros((2,2,2,3),np.uint8); rgb[:,0,0]=255
    fg=np.zeros((2,2,2),bool); fg[:,0,0]=True
    result=score({"task":"dynamics"},{"rgb":np.zeros_like(rgb)},
                 {"rgb":rgb,"valid":np.ones((2,2,2),bool),"foreground":fg})
    assert result["rgb_mae"] == .25 and result["foreground_mae"] == 1.


@pytest.mark.parametrize("mode", ["missing", "failed", "invalid-shape", "nonfinite"])
def test_failed_cases_remain_in_denominator(run, mode):
    m,t,s=run; sub=read_json(s); ident="room-000-geometry"
    if mode == "missing": del sub["cases"][ident]; rewrite(s,sub)
    elif mode == "failed": sub["cases"][ident]={"status":"failed"}; rewrite(s,sub)
    else:
        arr=np.full((2,32,48), np.nan if mode=="nonfinite" else 0., dtype=np.float32)
        if mode == "invalid-shape": arr=arr[:1]
        changed_array(s,ident,s.parent,{"depth":arr})
    report=measure(*run)
    assert report["measurements"]["assigned"]==10 and report["measurements"]["successful"]==9
    group=report["measurements"]["tasks"]["geometry"]
    assert group["failed"]==1 and group["world_values"]["room-000"]["depth_relative_error_bounded"]==1.


def test_changed_prediction_aborts_instead_of_hiding_integrity_failure(run):
    m,t,s=run; sub=read_json(s); row=next(iter(sub["cases"].values()))
    path=s.parent/row["output"]["path"]; path.write_bytes(path.read_bytes()+b"change")
    with pytest.raises(InvalidEvidence,match="hash mismatch"): measure(*run)


@pytest.mark.parametrize("change", ["target-hash", "missing-target", "wrong-dataset", "extra-submission"])
def test_changed_or_incomplete_scope_aborts(run, change):
    m,t,s=run
    if change in ("target-hash","missing-target"):
        doc=read_json(t); key=next(iter(doc["cases"]))
        if change=="target-hash": doc["cases"][key]["sha256"]="0"*64
        else: del doc["cases"][key]
        rewrite(t,doc)
    else:
        doc=read_json(s)
        if change=="wrong-dataset": doc["dataset_sha256"]="0"*64
        else: doc["cases"]["unassigned"]={"status":"failed"}
        rewrite(s,doc)
    with pytest.raises(InvalidEvidence): measure(*run)


def test_empty_valid_targets_abort(run):
    m,t,s=run; idx=read_json(t); ident="room-000-spatial"
    arrays=load_arrays(t.parent/idx["cases"][ident]["path"]); arrays["valid"][:]=False
    changed_array(t,ident,t.parent,arrays)
    with pytest.raises(InvalidEvidence,match="nonempty"): measure(*run)


def test_ground_truth_arrays_not_in_public_inputs(run):
    m,t,s=run; doc,_=dataset(m)
    for case in doc["cases"]:
        inputs=load_arrays(m.parent/case["input"]["path"])
        assert not ({"depth","points","target","foreground","future_rgb"} & set(inputs))


def test_query_target_cannot_be_added_to_inputs(run):
    m,t,s=run; doc=read_json(m); case=doc["cases"][0]; path=m.parent/case["input"]["path"]
    arrays=load_arrays(path); arrays["future_rgb"]=arrays["rgb"]
    np.savez_compressed(path,**arrays); case["input"]["sha256"]=file_hash(path); rewrite(m,doc)
    with pytest.raises(InvalidEvidence,match="target-like"): dataset(m)


def test_persistence_camera_contract(run):
    m,t,s=run; doc=read_json(m); case=next(c for c in doc["cases"] if c["task"]=="persistence")
    path=m.parent/case["input"]["path"]; arrays=load_arrays(path)
    arrays["query_camera_to_world"][-1,0,3]+=1
    np.savez_compressed(path,**arrays); case["input"]["sha256"]=file_hash(path); rewrite(m,doc)
    with pytest.raises(InvalidEvidence,match="return"): dataset(m)


def test_dynamics_requires_future_times(run):
    m,t,s=run; doc=read_json(m); case=next(c for c in doc["cases"] if c["task"]=="dynamics")
    case["timestamps_s"]=[0.,.1,.2]; rewrite(m,doc)
    with pytest.raises(InvalidEvidence,match="before forecast"): dataset(m)


def test_world_bootstrap_is_reproducible_and_single_world_not_overconfident():
    assert interval([0.,1.]) == interval([0.,1.])
    assert interval([0.,1.])["mean"] == .5
    assert interval([.2])["ci95"] is None


def test_worlds_are_equally_weighted_even_with_duplicate_views(run):
    m,t,s=run
    # Three cases from one world must not outweigh one from another world.
    manifest=read_json(m); targets=read_json(t); sub=read_json(s)
    case=next(c for c in manifest["cases"] if c["id"]=="room-000-geometry")
    target=load_arrays(t.parent/targets["cases"][case["id"]]["path"])
    changed_array(s,case["id"],s.parent,{"depth":target["depth"]})
    sub=read_json(s)
    for suffix in ("a","b"):
        new=dict(case,id=case["id"]+suffix)
        manifest["cases"].append(new)
        targets["cases"][new["id"]]=targets["cases"][case["id"]]
        sub["cases"][new["id"]]=sub["cases"][case["id"]]
    sub["cases"]["room-001-geometry"]={"status":"failed"}
    rewrite(m,manifest)
    targets["dataset_sha256"]=sub["dataset_sha256"]=file_hash(m)
    rewrite(t,targets); rewrite(s,sub)
    group=measure(*run)["measurements"]["tasks"]["geometry"]
    assert group["assigned"]==4
    assert group["metrics"]["depth_relative_error_bounded"]["mean"]==.5
    assert group["metrics"]["depth_relative_error_bounded"]["world_count"]==2


def test_editing_cannot_compare_an_unmatched_camera(run):
    m,t,s=run; doc=read_json(m); case=next(c for c in doc["cases"] if c["task"]=="editing")
    path=m.parent/case["input"]["path"]; arrays=load_arrays(path)
    arrays["query_camera_to_world"][0,0,3]+=.5
    np.savez_compressed(path,**arrays); case["input"]["sha256"]=file_hash(path); rewrite(m,doc)
    with pytest.raises(InvalidEvidence,match="last observation camera"): dataset(m)


def test_compare_rejects_unmatched_versions_and_replay_detects_tampering(run,tmp_path):
    output=tmp_path/"a"; evaluate(*run,output)
    same=compare(output/"report.json",output/"report.json")
    assert all(m["mean"]==0 for task in same["paired_world_intervals"].values() for m in task.values())
    doc=read_json(output/"report.json"); doc["dataset_sha256"]="0"*64
    rewrite(tmp_path/"other.json",doc)
    with pytest.raises(InvalidEvidence,match="Unmatched"): compare(output/"report.json",tmp_path/"other.json")
    with pytest.raises(InvalidEvidence,match="Replay differs"): replay(*run,tmp_path/"other.json")


def test_report_escapes_model_names(run,tmp_path):
    m,t,s=run; sub=read_json(s); sub["system"]["name"]='<script>alert("x")</script>'; rewrite(s,sub)
    evaluate(*run,tmp_path/"report")
    html=(tmp_path/"report/report.html").read_text()
    assert '<script>alert' not in html and '&lt;script&gt;' in html


@pytest.mark.parametrize("path", ["../secret", "/etc/passwd", "a/../../b", "a\\b", "https://example.com", "a//b"])
def test_paths_reject_escape(tmp_path,path):
    with pytest.raises(InvalidEvidence): safe_file(tmp_path,path)


def test_symlink_and_object_archives_rejected(tmp_path):
    (tmp_path/"real").write_text("x"); (tmp_path/"link").symlink_to(tmp_path/"real")
    with pytest.raises(InvalidEvidence): safe_file(tmp_path,"link")
    np.savez(tmp_path/"object.npz", payload=np.array([{"x":1}],dtype=object))
    with pytest.raises(InvalidEvidence): load_arrays(tmp_path/"object.npz")


def test_duplicate_json_rejected(tmp_path):
    path=tmp_path/"dup.json"; path.write_text('{"id":1,"id":2}')
    with pytest.raises(InvalidEvidence,match="Duplicate"): read_json(path)


def test_large_header_rejected_before_numpy_allocation(tmp_path):
    stream=io.BytesIO()
    np.lib.format.write_array_header_1_0(stream,{'descr':'<f8','fortran_order':False,'shape':(2**40,)})
    with zipfile.ZipFile(tmp_path/"huge.npz","w") as archive: archive.writestr("rgb.npy",stream.getvalue())
    with pytest.raises(InvalidEvidence): load_arrays(tmp_path/"huge.npz")


def test_duplicate_archive_keys_rejected(tmp_path):
    stream=io.BytesIO(); np.save(stream,np.ones((1,)),allow_pickle=False)
    with zipfile.ZipFile(tmp_path/"dup.npz","w") as archive:
        archive.writestr("depth.npy",stream.getvalue())
        with pytest.warns(UserWarning): archive.writestr("depth.npy",stream.getvalue())
    with pytest.raises(InvalidEvidence,match="duplicate"): load_arrays(tmp_path/"dup.npz")


@pytest.mark.parametrize("convention,shape",[("mapanything-depth-z",(2,3,4,1)),("da3-depth",(2,3,4)),
                                           ("pi3-local-points",(1,2,3,4,3))])
def test_model_output_adapters_preserve_scale_and_axes(convention,shape):
    values=np.full(shape,2.,dtype=np.float32)
    out=depth_export(values,convention,scale_meters=3.)["depth"]
    assert out.shape==(2,3,4) and (out==6).all()


def test_unknown_or_nonmetric_output_conversion_rejected():
    with pytest.raises(InvalidEvidence): depth_export(np.ones((2,3,4)),"da3-depth",scale_meters=0)
    with pytest.raises(InvalidEvidence): depth_export(np.ones((2,3,4)),"mapanything-depth-z",scale_meters=1)


def test_refuse_overwriting_evidence(run,tmp_path):
    evaluate(*run,tmp_path/"report")
    with pytest.raises(FileExistsError): evaluate(*run,tmp_path/"report")


def test_controls_cannot_be_labelled_models(run,tmp_path):
    with pytest.raises(InvalidEvidence,match="learned"):
        predict(run[0],tmp_path/"model",adapter="last-frame",name="Model",revision="x")
