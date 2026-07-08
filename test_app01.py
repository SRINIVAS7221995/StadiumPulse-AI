# Test invalid input handling
def test_negative_values():

    tester = app.test_client()

    response = tester.post(
        '/',
        data={
            'distance': -10,
            'electricity': 50
        }
    )

    assert response.status_code == 200