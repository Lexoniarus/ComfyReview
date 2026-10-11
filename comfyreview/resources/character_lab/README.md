# Character Lab v8.2 – original authored character resources

C1 imports **unchanged bytes**, not the standalone Character Lab server or
its database. There are six JSON profiles (`characters/`), six original voice
prompts (`prompts/characters/`) and six source dossiers (`sources/`). The
`original_sha256.json` manifest records SHA-256 digests of each source file as
extracted from `ComfyReview_Character_Lab_DI_Refactor_v8_2.zip`.

`FileCharacterCatalog` validates this complete set on construction. It reads
and holds immutable typed records; it never updates source files. Revision
IDs consist of the first 16 SHA-256 hex characters: `source` hashes the source
bytes, `voice_prompt` hashes the original prompt bytes, and `profile` hashes
the profile bytes concatenated with the source revision. No edit operation is
provided in C1.

These dossiers contain **private and internal character facts**. Do not expose
`get_profile()`, `get_voice_prompt()` or `get_source_document()` through an
unauthorized route. Only `list_public()` and `get_public()` are deliberately
restricted projections; C1 registers **no HTTP routes**. Files in a public
source repository remain readable as source code even without an API route.

All personality proposals are unapproved experiments; non-null experimental
`base_personality_type` or `base_axis_vector` values fail closed in this C1
adapter. The source discrepancy for Saki (17 in the dossier versus 18+ for
future Academy entry) is preserved for a later explicit author decision.

## C2a prompt resources

The ten additional v8.2-authored text files are byte-preserved under
`prompts/global_speaker.md`, `prompts/variants/` and
`prompts/candidates/`. They are not replacements for
`prompts/characters/`. The read-only `FilePromptCatalog` validates
the complete resource set at construction and exposes full SHA-256 source
revisions. `CharacterPromptComposer` uses the already existing C1 catalog
as its only character-identity and original-voice source.

The default is `baseline` with the original voice. The only experimental
voice substitution is an explicit `voice_candidate_p2` selection and is
reported as `experimental_candidate` with a separate composition revision.
It never edits or promotes an original C1 voice. `voice_precise` changes
style guidance only. The result contains system instructions, **not** chat
history, RAG snippets, biographies or conversational messages.
