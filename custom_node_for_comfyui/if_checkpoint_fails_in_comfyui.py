class RandomLoadCheckpoint:
    # WAS IST DAS?
    # Helper Node: laedt einen Checkpoint dynamisch per Name.
    # Das ist notwendig, weil RandomSamplerSchedulerSteps checkpoint_name als STRING ausgibt.
    # Diese Node wandelt STRING -> MODEL CLIP VAE und gibt ckpt_name_out fuer Debugging zurueck.
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ckpt_name": ("STRING", {"default": ""}),
                "force_refresh": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING")
    RETURN_NAMES = ("model", "clip", "vae", "ckpt_name_out")
    FUNCTION = "load"
    CATEGORY = "alex_nodes"

    def load(self, ckpt_name, force_refresh=True):
        # WAS TUT ES?
        # Optional refresh der folder_paths Listen, dann Checkpoint in Comfy laden.
        # WO KOMMT ES HER?
        # ckpt_name aus RandomSamplerSchedulerSteps.
        # WO GEHT ES HIN?
        # model clip vae gehen in den restlichen Workflow.
        name = str(ckpt_name or "").strip()
        if not name:
            raise ValueError("ckpt_name ist leer")

        if force_refresh:
            for fn_name in ("refresh_all", "refresh_checkpoints", "refresh_path"):
                fn = getattr(folder_paths, fn_name, None)
                if callable(fn):
                    try:
                        fn()
                        break
                    except Exception:
                        pass

        available = []
        try:
            available = list(folder_paths.get_filename_list("checkpoints"))
        except Exception:
            available = []

        if available and name not in available:
            alt = [x for x in available if x.lower() == name.lower()]
            if alt:
                name = alt[0]
            else:
                raise ValueError(f"Checkpoint nicht gefunden: {name}")

        ckpt_path = folder_paths.get_full_path("checkpoints", name)
        if not ckpt_path:
            raise ValueError(f"Kein Pfad für Checkpoint: {name}")

        emb_paths = []
        try:
            emb_paths = folder_paths.get_folder_paths("embeddings") or []
        except Exception:
            emb_paths = []
        embedding_dir = emb_paths[0] if emb_paths else None

        out = comfy.sd.load_checkpoint_guess_config(
            ckpt_path,
            output_vae=True,
            output_clip=True,
            embedding_directory=embedding_dir,
        )
        model, clip, vae = out[0], out[1], out[2]
        return (model, clip, vae, name)


# WAS IST DAS?
# ComfyUI Node Registrierung.
NODE_CLASS_MAPPINGS = {
    "RandomLoadCheckpoint": RandomLoadCheckpoint,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoadCheckpoint": "RandomLoadCheckpoint",
}