-- Historical workflows, temporal evaluation and original multimodal source representations.
BEGIN TRANSACTION;
DEFINE FIELD OVERWRITE parser ON source_file TYPE option<string>;
DEFINE FIELD OVERWRITE raw_sha256 ON source_file TYPE option<string>;
DEFINE FIELD OVERWRITE raw_size ON source_file TYPE option<int>;
DEFINE FIELD OVERWRITE raw_content_base64 ON source_file TYPE option<string>;
DEFINE FIELD OVERWRITE multimodal ON source_file TYPE option<object> FLEXIBLE;
-- multimodal.input_block retains the exact provider image/PDF content representation;
-- multimodal.usage retains token counts. Provider-internal image token IDs are not exposed.
DEFINE TABLE OVERWRITE derived_from SCHEMAFULL TYPE RELATION IN email | call | workflow_case | workflow_event | media_asset OUT source_file ENFORCED;
DEFINE TABLE OVERWRITE has_event SCHEMAFULL TYPE RELATION IN workflow_case OUT workflow_event ENFORCED;
DEFINE TABLE OVERWRITE next_event SCHEMAFULL TYPE RELATION IN workflow_event OUT workflow_event ENFORCED;
DEFINE TABLE OVERWRITE has_transition SCHEMAFULL TYPE RELATION IN workflow_case OUT workflow_transition ENFORCED;
DEFINE TABLE OVERWRITE from_step SCHEMAFULL TYPE RELATION IN workflow_transition OUT workflow_event ENFORCED;
DEFINE TABLE OVERWRITE to_step SCHEMAFULL TYPE RELATION IN workflow_transition OUT workflow_event ENFORCED;
DEFINE TABLE OVERWRITE evaluates SCHEMAFULL TYPE RELATION IN workflow_evaluation OUT workflow_transition ENFORCED;
DEFINE TABLE OVERWRITE learned_from SCHEMAFULL TYPE RELATION IN skill_version OUT workflow_case ENFORCED;
DEFINE TABLE OVERWRITE exercises SCHEMAFULL TYPE RELATION IN workflow_case OUT skill ENFORCED;
DEFINE TABLE OVERWRITE used_skill SCHEMAFULL TYPE RELATION IN workflow_evaluation OUT skill_version ENFORCED;
DEFINE TABLE OVERWRITE has_triplet SCHEMAFULL TYPE RELATION IN workflow_case OUT workflow_triplet ENFORCED;
DEFINE TABLE OVERWRITE includes_event SCHEMAFULL TYPE RELATION IN workflow_triplet OUT workflow_event ENFORCED;
COMMIT TRANSACTION;
