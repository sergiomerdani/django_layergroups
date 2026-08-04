from django.urls import path

from .views import agent_manifest, chat, health_check, openai_key_status

urlpatterns = [
    path("health/", health_check, name="custom-api-health"),
    path("openai/status/", openai_key_status, name="openai-key-status"),
    path("agent/manifest/", agent_manifest, name="custom-api-agent-manifest"),
    path("chat/", chat, name="custom-api-chat"),
]
