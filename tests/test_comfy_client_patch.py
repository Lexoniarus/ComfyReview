from services.comfy_client import ComfyClient


def test_patch_workflow_for_run_patches_expected_nodes() -> None:
    client = ComfyClient(base_url="http://127.0.0.1:8188")

    workflow = {
        "26:24": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "old_pos"},
            "_meta": {"title": "Prompt"},
        },
        "25:24": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "old_neg"},
            "_meta": {"title": "Negative Prompt"},
        },
        "1": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 1,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "2": {"class_type": "name_meta_export", "inputs": {"subdir": "old"}},
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "oldckpt"}},
    }

    patched = client.patch_workflow_for_run(
        workflow,
        positive_prompt="NEW_POS",
        negative_prompt="NEW_NEG",
        subdir="playground",
        checkpoint="ckptA.safetensors",
        seed=123,
        steps=30,
        cfg=6.5,
        sampler="dpmpp_2m",
        scheduler="karras",
        denoise=0.75,
    )

    assert patched["26:24"]["inputs"]["value"] == "NEW_POS"
    assert patched["25:24"]["inputs"]["value"] == "NEW_NEG"

    ks = patched["1"]["inputs"]
    assert ks["seed"] == 123
    assert ks["steps"] == 30
    assert ks["cfg"] == 6.5
    assert ks["sampler_name"] == "dpmpp_2m"
    assert ks["scheduler"] == "karras"
    assert ks["denoise"] == 0.75

    assert patched["2"]["inputs"]["subdir"] == "playground"
    assert patched["3"]["inputs"]["ckpt_name"] == "ckptA.safetensors"


def test_patch_workflow_for_run_fallback_by_meta_title() -> None:
    client = ComfyClient(base_url="http://127.0.0.1:8188")

    workflow = {
        "a": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "old_pos"},
            "_meta": {"title": "prompt"},
        },
        "b": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": "old_neg"},
            "_meta": {"title": "negative prompt"},
        },
        "1": {"class_type": "KSampler", "inputs": {"seed": 1, "steps": 20, "cfg": 7.0}},
    }

    patched = client.patch_workflow_for_run(
        workflow,
        positive_prompt="P",
        negative_prompt="N",
        subdir="x",
    )

    assert patched["a"]["inputs"]["value"] == "P"
    assert patched["b"]["inputs"]["value"] == "N"
