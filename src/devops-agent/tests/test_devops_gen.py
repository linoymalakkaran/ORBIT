"""Tests for devops agent."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_generate_gitlab_ci_dotnet():
    from app.main import generate_gitlab_ci
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "service_type": "dotnet", "has_frontend": False,
        "gitlab_ci": "", "helm_chart": "", "kong_plugin_config": "",
        "argocd_app": "", "sonarqube_config": "", "trivy_config": "",
        "security_pipeline_stages": "",
    }
    result = await generate_gitlab_ci(state)
    assert "dotnet build" in result["gitlab_ci"]
    assert "harbor.ai.adports.ae/orbit" in result["gitlab_ci"]
    assert "deploy-prod" in result["gitlab_ci"]


@pytest.mark.asyncio
async def test_generate_gitlab_ci_python():
    from app.main import generate_gitlab_ci
    state = {
        "project_id": "p1", "service_name": "OrchestratorService",
        "service_type": "python", "has_frontend": False,
        "gitlab_ci": "", "helm_chart": "", "kong_plugin_config": "",
        "argocd_app": "", "sonarqube_config": "", "trivy_config": "",
        "security_pipeline_stages": "",
    }
    result = await generate_gitlab_ci(state)
    assert "poetry run pytest" in result["gitlab_ci"]
    assert "trivy-scan" in result["gitlab_ci"]


@pytest.mark.asyncio
async def test_generate_helm_chart():
    from app.main import generate_helm_chart
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "service_type": "dotnet", "has_frontend": False,
        "gitlab_ci": "", "helm_chart": "", "kong_plugin_config": "",
        "argocd_app": "", "sonarqube_config": "", "trivy_config": "",
        "security_pipeline_stages": "",
    }
    result = await generate_helm_chart(state)
    assert "harbor.ai.adports.ae/orbit/paymentservice" in result["helm_chart"]
    assert "harbor-pull-secret" in result["helm_chart"]
    assert "vault" in result["helm_chart"]
