"""Resolve official model revisions once, download and hash a local evaluation bundle."""
import argparse
from pathlib import Path
from evaluation_common import manifest, finish_manifest, write_json, sha256

MODEL_IDS = {"embedding": "intfloat/multilingual-e5-small", "reranker": "BAAI/bge-reranker-v2-m3",
             "nli": "joeddav/xlm-roberta-large-xnli"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, default=Path(".runtime/evaluation_models"))
    args = p.parse_args()
    from huggingface_hub import HfApi, snapshot_download
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    config_path = out / "models.json"
    if config_path.exists():
        raise ValueError("Existing pinned bundle; select another output directory.")
    api = HfApi()
    models = {}
    for role, model_id in MODEL_IDS.items():
        print(f"Resolving/downloading {role}: {model_id}", flush=True)
        revision = api.model_info(model_id).sha
        path = Path(snapshot_download(model_id, revision=revision, cache_dir=str(out / "cache"),
                                      allow_patterns=["*.json", "*.txt", "*.model", "*.safetensors", "pytorch_model.bin"],
                                      ignore_patterns=["onnx/*", "openvino/*", "*.h5", "*.msgpack"]))
        models[role] = {"model_id": model_id, "revision": revision, "path": str(path.resolve()),
                        "files_sha256": {f.relative_to(path).as_posix(): sha256(f) for f in path.rglob("*") if f.is_file()}}
    write_json(config_path, models)
    record = manifest(__file__)
    record["status"] = "MODELS_DOWNLOADED_AND_HASHED"
    # Hash model snapshots, not twice via cache symlinks and blobs.
    record["models"] = models
    write_json(out / "acquisition_manifest.json", record)
    print(f"Pinned models: {config_path}")


if __name__ == "__main__":
    main()
