# Voice: ElevenLabs with the existing Vonage number

Vonage supplies the phone number and PSTN connection. ElevenLabs runs the live
conversation and connects directly to Vonage over SIP. This FastAPI service
starts calls, prepares caller context, exposes session-scoped tools, and ingests
signed post-call transcripts. It does not carry audio and needs no SIP/WebSocket
bridge container.

```text
Outbound: Properly voice --HTTPS--> ElevenLabs --SIP--> Vonage --> recipient
Inbound:  caller --> Vonage number --SIP--> ElevenLabs agent
Context, tools and transcripts: ElevenLabs --HTTPS--> Properly voice
```

## One-time provider setup

1. In Vonage, create or reuse a SIP trunk. Enable outbound digest authentication
   and record its username, password and regional endpoint, for example
   `your-trunk.sip-eu.vonage.com`. SIP credentials are configured on the trunk;
   they are distinct from the account API key and secret.
2. In ElevenLabs Agents, import your existing Vonage number as a **SIP trunk**
   number. Set its outbound address to the Vonage regional hostname (without
   `sip:`), and enter the trunk's digest credentials. Use TLS transport and SRTP;
   both providers support PCMA/PCMU. Assign your ElevenLabs agent to this number.
3. In Vonage's inbound trunk settings, add the ElevenLabs destination, for example
   `sip:+44YOURNUMBER@sip.rtc.elevenlabs.io:5061;transport=tls`, enable SRTP and link
   the existing number. Use the destination shown by ElevenLabs for your workspace.
   The number in the SIP URI must exactly match the imported number, including
   its leading `+`. Linking the number replaces any previous inbound routing.
   Configure ElevenLabs inbound authentication/access controls to match Vonage's
   delivery configuration; outbound trunk credentials do not automatically secure
   the inbound direction.
4. Configure the ElevenLabs agent's conversation-initiation webhook as
   `https://VOICE_HOST/webhooks/elevenlabs/initiation`. Send
   `X-Webhook-Secret: <ELEVENLABS_TOOL_SECRET>`. Configure its server tools under
   `https://VOICE_HOST/tools/voice/{name}` with the same header and the `run_id`
   dynamic variable. The agent uses `brief`, `objective`, `contact_name` and
   `run_id`; the initiation response supplies these for inbound calls.
5. Configure the ElevenLabs post-call transcription webhook as
   `https://VOICE_HOST/webhooks/elevenlabs/post-call` and store its HMAC signing
   secret as `ELEVENLABS_WEBHOOK_SECRET`. This is separate from the tool secret.

The equivalent management APIs are Vonage's
[`/v1/psip/`](https://developer.vonage.com/en/api/psip) and ElevenLabs'
[`POST /v1/convai/phone-numbers`](https://elevenlabs.io/docs/api-reference/phone-numbers/create).
For the ElevenLabs import, use `provider: "sip_trunk"`, `agent_id`, `phone_number`,
`label`, `inbound_trunk_config` and `outbound_trunk_config`. Outbound configuration
contains `address`, `transport: "tls"`, `media_encryption: "required"` and
`credentials: {username, password}`. Save the returned `phone_number_id`.

## Application configuration

Populate these variables in the root `.env` for `make dev` or `make dev-docker`:

```dotenv
ELEVENLABS_API_KEY=
ELEVENLABS_AGENT_ID=
ELEVENLABS_PHONE_NUMBER_ID=
ELEVENLABS_TOOL_SECRET=
ELEVENLABS_WEBHOOK_SECRET=
```

`ELEVENLABS_PHONE_NUMBER_ID` is the ID returned by ElevenLabs after importing the
Vonage number, not the E.164 phone number. `sip-trunk` (hyphen) is the outbound
API path; `sip_trunk` (underscore) is the provider value used only when importing.
The application calls `POST /v1/convai/sip-trunk/outbound-call` with the existing
brief and session variables. There is no runtime carrier selector.

For Cloud Run, put the three ElevenLabs secrets in the existing voice Secret
Manager bindings and the agent ID and number ID in
`service_environment.voice`. Vonage's API secret is only needed for provisioning
through its management API. The voice service uses ElevenLabs credentials at
runtime; Vonage SIP credentials are stored in ElevenLabs' trunk configuration.
Local webhooks need a public HTTPS tunnel to the voice port printed by `make dev`.

## Verification

`uv run --locked pytest tests/test_voice.py` checks the outbound SIP request,
missing credentials, caller lookup, tool
authentication and signed transcript ingestion with mocked provider HTTP calls.
These tests do not validate account provisioning or live audio.

Before relying on the number, test an outbound call to a controlled recipient and
an inbound call to the Vonage number. Confirm caller ID, two-way audio, caller
context, tool/session access and transcript delivery. ElevenLabs documents
`X-CALL-ID` and `X-CALLER-ID` for SIP personalization; inspect the real initiation
payload to verify that Vonage's caller metadata arrives correctly. Unknown or
withheld callers receive the generic brief. Verify timeout/failure behaviour on
the configured agent as well as the successful path.

Provider references:

- [ElevenLabs SIP trunking and supported providers](https://elevenlabs.io/docs/eleven-agents/phone-numbers/sip-trunking)
- [ElevenLabs SIP outbound calls](https://elevenlabs.io/docs/api-reference/sip-trunk/outbound-call)
- [Vonage inbound and outbound configuration](https://developer.vonage.com/en/sip/sip-dashboard)
- [Vonage transports and codecs](https://developer.vonage.com/en/sip/technical-details)
