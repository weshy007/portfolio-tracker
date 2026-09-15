"""Tests for API calculation endpoints."""
import pytest
from decimal import Decimal


def test_emergency_fund_calculation(client):
    """Test emergency fund calculation endpoint."""
    response = client.post(
        "/api/calculate/emergency-fund",
        json={
            "essential_monthly_expenses": 30000,
            "target_months": 6,
            "current_emergency_fund": 90000,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["target"]) == 180000.0  # 30000 * 6
    assert float(data["current"]) == 90000.0
    assert float(data["remaining"]) == 90000.0
    assert data["percentage_complete"] == 50.0
    assert data["months_covered"] == 3.0
    assert data["is_fully_funded"] is False


def test_same_currency_rate_needs_no_external_provider(client):
    """Currency endpoint accepts a pair only and serves an identity rate locally."""
    response = client.get("/api/currency/rate?from_currency=kes&to_currency=KES")
    assert response.status_code == 200
    data = response.json()
    assert data["from_currency"] == "KES"
    assert data["to_currency"] == "KES"
    assert float(data["rate"]) == 1.0


def test_emergency_fund_fully_funded(client):
    """Test emergency fund when fully funded."""
    response = client.post(
        "/api/calculate/emergency-fund",
        json={
            "essential_monthly_expenses": 20000,
            "target_months": 6,
            "current_emergency_fund": 120000,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["target"]) == 120000.0
    assert data["is_fully_funded"] is True
    assert data["excess"] == 0.0


def test_emergency_fund_zero_expenses(client):
    """Test emergency fund with zero expenses."""
    response = client.post(
        "/api/calculate/emergency-fund",
        json={
            "essential_monthly_expenses": 0,
            "target_months": 6,
            "current_emergency_fund": 10000,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["target"]) == 0.0
    assert data["months_covered"] == 0.0


def test_allocation_calculation(client):
    """Test allocation calculation endpoint."""
    response = client.post(
        "/api/calculate/allocation",
        json={
            "total_income": 100000,
            "expenses": 40000,
            "savings": 30000,
            "investments": 20000,
            "debt": 5000,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["total_allocated"]) == 95000.0
    assert float(data["unallocated"]) == 5000.0
    assert data["percentage_allocated"] == 95.0


def test_allocation_overallocated(client):
    """Test allocation when overallocated."""
    response = client.post(
        "/api/calculate/allocation",
        json={
            "total_income": 100000,
            "expenses": 60000,
            "savings": 30000,
            "investments": 20000,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["overallocated"]) == 10000.0
    assert data["percentage_allocated"] == 110.0


def test_projection_calculation(client):
    """Test financial projection calculation."""
    response = client.post(
        "/api/calculate/projection",
        json={
            "monthly_contribution": 10000,
            "annual_return_percent": 0,
            "years": 1,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # With 0% return, should be: 10000 * 12 = 120000
    assert float(data["projected_value"]) == 120000.0
    assert float(data["total_contributions"]) == 120000.0
    assert float(data["total_returns"]) == 0.0


def test_projection_with_returns(client):
    """Test projection with positive returns."""
    response = client.post(
        "/api/calculate/projection",
        json={
            "monthly_contribution": 10000,
            "annual_return_percent": 12,
            "years": 5,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["projected_value"]) > float(data["total_contributions"])
    assert float(data["total_returns"]) > 0


def test_savings_rate_calculation(client):
    """Test savings rate calculation."""
    response = client.post(
        "/api/calculate/savings-rate",
        json={
            "savings_amount": 30000,
            "total_income": 100000,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["savings_rate_percent"] == 30.0


def test_savings_rate_zero_income(client):
    """Test savings rate with zero income."""
    response = client.post(
        "/api/calculate/savings-rate",
        json={
            "savings_amount": 10000,
            "total_income": 0,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["savings_rate_percent"] == 0.0


def test_net_worth_calculation(client):
    """Test net worth calculation."""
    response = client.post(
        "/api/calculate/net-worth",
        json={
            "total_assets": 500000,
            "total_liabilities": 200000,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["net_worth"]) == 300000.0


def test_net_worth_negative(client):
    """Test net worth when liabilities exceed assets."""
    response = client.post(
        "/api/calculate/net-worth",
        json={
            "total_assets": 100000,
            "total_liabilities": 150000,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["net_worth"]) == -50000.0


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "app" in data
    assert "environment" in data
