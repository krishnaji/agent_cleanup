# Agent Info: docupload

This artifact contains the configuration details and status of the registered Gemini Enterprise agent, retrieved via the Discovery Engine REST API.

## 🛠️ Metadata Summary

| Attribute | Value |
| :--- | :--- |
| **Agent Name** | `docupload` |
| **Agent ID** | `2341779122668799975` |
| **Project Number** | `554514247611` |
| **Project ID** | `genai-380800` |
| **Engine ID** | `enterprise-search-17371960_1737196020664` |
| **State** | `PRIVATE` |
| **Model** | `gemini-3.5-flash` |
| **Created** | `2026-06-29T13:41:10.991898Z` |
| **Last Updated** | `2026-06-29T13:42:05.059723964Z` |

---

## 📂 Deployed Files

The agent currently has access to the following documents for interaction and search grounding:

1. **`google_cloud_ai_events_2026.docx`**
   - **Type**: Microsoft Word (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
   - **Resource Path**: `projects/554514247611/locations/global/collections/default_collection/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/2341779122668799975/files/667100891105277657`

2. **`Corporate Rates 2026 Master Vendor Rate Card`**
   - **Type**: Microsoft Excel (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
   - **Resource Path**: `projects/554514247611/locations/global/collections/default_collection/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/2341779122668799975/files/1458442253120368743`

---

## 📡 Executed Curl Request

```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: 554514247611" \
  "https://global-discoveryengine.googleapis.com/v1alpha/projects/554514247611/locations/global/collections/default_collection/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/2341779122668799975"
```

---

## 📄 API Output JSON

```json
{
  "name": "projects/554514247611/locations/global/collections/default_collection/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/2341779122668799975",
  "displayName": "docupload",
  "description": "Agent to help interact with enterprise data.",
  "icon": {
    "content": ""
  },
  "createTime": "2026-06-29T13:41:10.991898Z",
  "updateTime": "2026-06-29T13:42:05.059723964Z",
  "state": "PRIVATE",
  "lowCodeAgentDefinition": {
    "nodes": [
      {
        "llmAgentNode": {
          "model": "gemini-3.5-flash",
          "instruction": "docupload",
          "googleSearchDisabled": true
        },
        "id": "root_agent",
        "displayName": "docupload"
      }
    ],
    "rootAgentId": "root_agent",
    "deployedNodes": [
      {
        "llmAgentNode": {
          "model": "gemini-3.5-flash",
          "instruction": "docupload",
          "googleSearchDisabled": true
        },
        "id": "root_agent",
        "displayName": "docupload"
      }
    ],
    "deployedRootAgentId": "root_agent",
    "draftDisplayName": "docupload",
    "draftIcon": {
      "content": ""
    },
    "draftDescription": "Agent to help interact with enterprise data.",
    "agentFiles": [
      {
        "name": "projects/554514247611/locations/global/collections/default_collection/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/2341779122668799975/files/667100891105277657",
        "fileName": "google_cloud_ai_events_2026.docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      },
      {
        "name": "projects/554514247611/locations/global/collections/default_collection/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/2341779122668799975/files/1458442253120368743",
        "fileName": "Corporate Rates 2026 Master Vendor Rate Card",
        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      }
    ],
    "deployedAgentFiles": [
      {
        "name": "projects/554514247611/locations/global/collections/default_collection/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/2341779122668799975/files/667100891105277657",
        "fileName": "google_cloud_ai_events_2026.docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      },
      {
        "name": "projects/554514247611/locations/global/collections/default_collection/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/2341779122668799975/files/1458442253120368743",
        "fileName": "Corporate Rates 2026 Master Vendor Rate Card",
        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      }
    ]
  },
  "agentIdentityInfo": {
    "spiffeIdType": "USER",
    "spiffeId": "//agents.global.org-294415378404.system.id.goog/resources/discoveryengine/projects/554514247611/locations/global/engines/enterprise-search-17371960_1737196020664/assistants/default_assistant/agents/user/2341779122668799975",
    "agentIdPart": "2341779122668799975"
  }
}
```
