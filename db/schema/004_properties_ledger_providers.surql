-- Addendum A. Financial content is immutable; a privileged API may advance status.
-- Table/field permissions protect record users, not root/database system users.
-- Events enforce financial immutability for every access level as well.
BEGIN TRANSACTION;
DEFINE TABLE OVERWRITE transaction SCHEMAFULL CHANGEFEED 7d INCLUDE ORIGINAL
    PERMISSIONS FOR select, create FULL FOR update, delete NONE;
DEFINE EVENT OVERWRITE transaction_no_delete ON transaction
    WHEN $event = 'DELETE' THEN { THROW 'Ledger entries cannot be deleted; append a reversal'; };
DEFINE EVENT OVERWRITE transaction_immutable ON transaction
    WHEN $event = 'UPDATE' AND (
        $before.ref != $after.ref OR $before.external_ref != $after.external_ref OR
        $before.kind != $after.kind OR $before.category != $after.category OR
        $before.amount_minor != $after.amount_minor OR $before.currency != $after.currency OR
        $before.effective_date != $after.effective_date OR $before.period_start != $after.period_start OR
        $before.period_end != $after.period_end OR $before.payment_method != $after.payment_method OR
        $before.bank_account != $after.bank_account OR $before.counterparty_name != $after.counterparty_name OR
        $before.description != $after.description OR $before.notes != $after.notes OR
        $before.recorded_by != $after.recorded_by OR
        $before.adjustment_deltas != $after.adjustment_deltas OR $before.name != $after.name OR
        $before.aliases != $after.aliases OR
        $before.created_at != $after.created_at OR $before.merged_into != $after.merged_into
    ) THEN { THROW 'Ledger financial fields are immutable; append a reversal'; };
-- Evidence may accumulate and confidence may rise after matching a bank source.
-- Previously stored evidence and external reference bindings must remain intact.
DEFINE EVENT OVERWRITE transaction_provenance_append ON transaction
    WHEN $event = 'UPDATE' AND (
        ($after.confidence ?? 0) < ($before.confidence ?? 0) OR
        NOT (object::entries($after.external_ids) CONTAINSALL object::entries($before.external_ids)) OR
        NOT (($after.evidence ?? []) CONTAINSALL ($before.evidence ?? []))
    ) THEN { THROW 'Ledger provenance may only be appended and confidence may only rise'; };
DEFINE EVENT OVERWRITE transaction_status_forward ON transaction
    WHEN $event = 'UPDATE' AND $before.status != $after.status AND NOT (
        ($before.status = 'expected' AND $after.status IN ['pending', 'cleared', 'reconciled', 'void']) OR
        ($before.status = 'pending' AND $after.status IN ['cleared', 'reconciled', 'void']) OR
        ($before.status = 'cleared' AND $after.status IN ['reconciled', 'void'])
    ) THEN { THROW 'Transaction status may only advance'; };
-- Stored balance caches can be refreshed by the privileged ledger transaction.
-- Literal READONLY would prevent refreshing them even from that transaction.
DEFINE FIELD OVERWRITE tenant_balance_minor ON property TYPE int DEFAULT 0 PERMISSIONS FOR update NONE;
DEFINE FIELD OVERWRITE landlord_balance_minor ON property TYPE int DEFAULT 0 PERMISSIONS FOR update NONE;
DEFINE FIELD OVERWRITE deposit_held_minor ON property TYPE int DEFAULT 0 PERMISSIONS FOR update NONE;
DEFINE TABLE OVERWRITE `for` SCHEMAFULL TYPE RELATION IN transaction | quote OUT property | ticket ENFORCED;
DEFINE TABLE OVERWRITE settles SCHEMAFULL TYPE RELATION IN transaction OUT transaction ENFORCED;
DEFINE FIELD OVERWRITE amount_minor ON settles TYPE int ASSERT $value > 0;
DEFINE TABLE OVERWRITE reverses SCHEMAFULL TYPE RELATION IN transaction OUT transaction ENFORCED;
DEFINE INDEX OVERWRITE reversal_unique ON reverses FIELDS out UNIQUE;
DEFINE TABLE OVERWRITE owns SCHEMAFULL TYPE RELATION IN person | company OUT property ENFORCED;
DEFINE FIELD OVERWRITE share_pct ON owns TYPE decimal DEFAULT 100 ASSERT $value > 0 AND $value <= 100;
DEFINE TABLE OVERWRITE tenant_of SCHEMAFULL TYPE RELATION IN person OUT property ENFORCED;
DEFINE FIELD OVERWRITE `from` ON tenant_of TYPE option<datetime>;
DEFINE FIELD OVERWRITE `to` ON tenant_of TYPE option<datetime>;
DEFINE FIELD OVERWRITE is_lead_tenant ON tenant_of TYPE bool DEFAULT false;
DEFINE TABLE OVERWRITE manages SCHEMAFULL TYPE RELATION IN company OUT property ENFORCED;
DEFINE TABLE OVERWRITE at SCHEMAFULL TYPE RELATION IN ticket OUT property ENFORCED;
DEFINE TABLE OVERWRITE offers SCHEMAFULL TYPE RELATION IN service_provider OUT service_offering ENFORCED;
DEFINE TABLE OVERWRITE contact SCHEMAFULL TYPE RELATION IN service_provider OUT person ENFORCED;
DEFINE FIELD OVERWRITE role ON contact TYPE string;
DEFINE TABLE OVERWRITE registered_as SCHEMAFULL TYPE RELATION IN service_provider OUT company ENFORCED;
DEFINE TABLE OVERWRITE covers SCHEMAFULL TYPE RELATION IN service_provider OUT property ENFORCED;
DEFINE TABLE OVERWRITE preferred_for SCHEMAFULL TYPE RELATION IN service_provider OUT property ENFORCED;
DEFINE TABLE OVERWRITE same_building SCHEMAFULL TYPE RELATION IN property OUT property ENFORCED;
DEFINE TABLE OVERWRITE assigned_to SCHEMAFULL TYPE RELATION IN ticket OUT service_provider ENFORCED;
DEFINE TABLE OVERWRITE `from` SCHEMAFULL TYPE RELATION IN quote OUT service_provider ENFORCED;
DEFINE TABLE OVERWRITE accepted_as SCHEMAFULL TYPE RELATION IN quote OUT transaction ENFORCED;
DEFINE TABLE OVERWRITE paid_by SCHEMAFULL TYPE RELATION IN transaction OUT person | company ENFORCED;
DEFINE TABLE OVERWRITE paid_to SCHEMAFULL TYPE RELATION IN transaction OUT person | company | service_provider ENFORCED;
DEFINE TABLE OVERWRITE for_ticket SCHEMAFULL TYPE RELATION IN transaction OUT ticket ENFORCED;
DEFINE TABLE OVERWRITE evidenced_by SCHEMAFULL TYPE RELATION IN transaction | service_offering OUT chunk ENFORCED;
DEFINE TABLE OVERWRITE about SCHEMAFULL TYPE RELATION IN email | call OUT property | service_provider ENFORCED;
DEFINE TABLE OVERWRITE derived_from SCHEMAFULL TYPE RELATION IN email | call | transaction OUT source_file ENFORCED;
DEFINE TABLE OVERWRITE mentions SCHEMAFULL TYPE RELATION IN chunk OUT person | company | ticket | email | call | property | transaction | service_provider | service_offering | quote ENFORCED CHANGEFEED 7d INCLUDE ORIGINAL;
-- Existing databases keep the historical location field until a safe backfill.
-- New canonical writes and extraction use location_detail and the at relation.
UPDATE ticket SET location_detail = location WHERE location != NONE;
REMOVE FIELD IF EXISTS location ON ticket;
COMMIT TRANSACTION;
