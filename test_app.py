# Import the Flask application
from app import app

# Test that the home page is accessible
def test_home_page():

    # Create Flask test client
    tester = app.test_client()

    # Request the home page
    response = tester.get('/')

    # Check HTTP success status
    assert response.status_code == 200


# Test carbon calculator form submission
def test_carbon_calculator():

    # Create Flask test client
    tester = app.test_client()

    # Submit sample user data
    response = tester.post(
        '/',
        data={
            'distance': 20,
            'electricity': 100
        }
    )

    # Verify successful response
    assert response.status_code == 200

    # Verify result appears on page
    assert b'Carbon Score' in response.data