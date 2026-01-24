"""
GraphGuard - API Integration Tests
====================================
File: tests/integration/test_api.py

Integration tests for FastAPI and GraphQL endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient
from datetime import datetime


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def api_client():
    """Create test client for FastAPI."""
    os.environ["API_KEY"] = "test-key"
    from ml.serving.api import app
    client = TestClient(app)
    client.headers.update({"X-API-Key": "test-key"})
    return client


@pytest.fixture
def sample_transaction():
    """Sample transaction request."""
    return {
        "transaction_id": "txn_test_001",
        "user_id": "user_123",
        "merchant_id": "merchant_456",
        "amount": 150.00,
        "currency": "USD",
        "device_id": "device_789",
        "ip_address": "192.168.1.1"
    }


# ============================================
# Health Check Tests
# ============================================

class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_returns_200(self, api_client):
        """Test health endpoint returns 200."""
        response = api_client.get("/health")
        assert response.status_code == 200
    
    def test_health_response_structure(self, api_client):
        """Test health response has expected fields."""
        response = api_client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert "model_loaded" in data
        assert "version" in data


# ============================================
# Score Endpoint Tests
# ============================================

class TestScoreEndpoint:
    """Tests for /score endpoint."""
    
    def test_score_returns_200(self, api_client, sample_transaction):
        """Test score endpoint returns 200."""
        response = api_client.post("/score", json=sample_transaction)
        assert response.status_code == 200
    
    def test_score_response_structure(self, api_client, sample_transaction):
        """Test score response has expected fields."""
        response = api_client.post("/score", json=sample_transaction)
        data = response.json()
        
        assert "transaction_id" in data
        assert "fraud_score" in data
        assert "decision" in data
        assert "latency_ms" in data
        assert "model_version" in data
        assert "explanation" in data
    
    def test_fraud_score_range(self, api_client, sample_transaction):
        """Test fraud score is between 0 and 1."""
        response = api_client.post("/score", json=sample_transaction)
        data = response.json()
        
        assert 0 <= data["fraud_score"] <= 1
    
    def test_decision_values(self, api_client, sample_transaction):
        """Test decision is one of expected values."""
        response = api_client.post("/score", json=sample_transaction)
        data = response.json()
        
        assert data["decision"] in ["AUTO_APPROVE", "REVIEW", "AUTO_DECLINE"]
    
    def test_latency_reasonable(self, api_client, sample_transaction):
        """Test latency is reasonable (<500ms)."""
        response = api_client.post("/score", json=sample_transaction)
        data = response.json()
        
        assert data["latency_ms"] < 500
    
    def test_invalid_amount_rejected(self, api_client, sample_transaction):
        """Test negative amount is rejected."""
        sample_transaction["amount"] = -100
        response = api_client.post("/score", json=sample_transaction)
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_field_rejected(self, api_client):
        """Test missing required field is rejected."""
        incomplete = {
            "transaction_id": "txn_001",
            "user_id": "user_123"
            # Missing other required fields
        }
        response = api_client.post("/score", json=incomplete)
        
        assert response.status_code == 422


# ============================================
# Caching Tests
# ============================================

class TestCaching:
    """Tests for Redis caching behavior."""
    
    def test_second_request_faster(self, api_client, sample_transaction):
        """Test cached requests are faster."""
        # First request
        response1 = api_client.post("/score", json=sample_transaction)
        latency1 = response1.json()["latency_ms"]
        
        # Second request (should be cached)
        response2 = api_client.post("/score", json=sample_transaction)
        latency2 = response2.json()["latency_ms"]
        
        # Cached should be faster or indicate cached
        if response2.json().get("cached"):
            assert latency2 <= latency1
    
    def test_different_users_not_cached(self, api_client, sample_transaction):
        """Test different users don't share cache."""
        # First user
        sample_transaction["user_id"] = "user_a"
        response1 = api_client.post("/score", json=sample_transaction)
        
        # Different user
        sample_transaction["user_id"] = "user_b"
        response2 = api_client.post("/score", json=sample_transaction)
        
        # Second should not be cached
        assert not response2.json().get("cached", False)


# ============================================
# GraphQL Tests
# ============================================

class TestGraphQL:
    """Tests for GraphQL API."""
    
    @pytest.fixture
    def graphql_client(self):
        """Create test client for GraphQL."""
        os.environ["API_KEY"] = "test-key"
        from strawberry.fastapi import GraphQLRouter
        from backend.graphql.resolvers import schema
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        def graphql_context_getter(request: Request):
            return {"request": request}

        graphql_app = GraphQLRouter(schema, context_getter=graphql_context_getter)
        app.include_router(graphql_app, prefix="/graphql")

        client = TestClient(app)
        client.headers.update({"X-API-Key": "test-key"})
        return client
    
    def test_fraud_queue_query(self, graphql_client):
        """Test fraudQueue query."""
        query = """
        query {
            fraudQueue(limit: 10) {
                items {
                    id
                    fraudScore
                    status
                }
                totalCount
            }
        }
        """
        
        response = graphql_client.post(
            "/graphql",
            json={"query": query}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "fraudQueue" in data["data"]
        assert "items" in data["data"]["fraudQueue"]
        assert "totalCount" in data["data"]["fraudQueue"]
    
    def test_fraud_case_query(self, graphql_client):
        """Test fraudCase query."""
        query = """
        query {
            fraudCase(id: "case_001") {
                id
                fraudScore
                status
                priority
            }
        }
        """
        
        response = graphql_client.post(
            "/graphql",
            json={"query": query}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "fraudCase" in data["data"]
    
    def test_shap_explanation_query(self, graphql_client):
        """Test shapExplanation query."""
        query = """
        query {
            shapExplanation(transactionId: "txn_001") {
                transactionId
                baseValue
                predictionValue
                plainEnglish
                features {
                    name
                    shapValue
                }
            }
        }
        """
        
        response = graphql_client.post(
            "/graphql",
            json={"query": query}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "shapExplanation" in data["data"]
        assert "features" in data["data"]["shapExplanation"]
    
    def test_label_case_mutation(self, graphql_client):
        """Test labelCase mutation."""
        mutation = """
        mutation {
            labelCase(id: "case_001", label: FRAUD, notes: "Test") {
                id
                status
            }
        }
        """
        
        response = graphql_client.post(
            "/graphql",
            json={"query": mutation}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data" in data
        assert "labelCase" in data["data"]


# ============================================
# Run Tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
