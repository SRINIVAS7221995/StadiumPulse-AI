from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():

    result = ""
    suggestion = ""

    if request.method == 'POST':

        vehicle = request.form['vehicle']
        distance = float(request.form['distance'])
        electricity = float(request.form['electricity'])

        factors = {
            "Bike": 0.10,
            "Car": 0.21,
            "Bus": 0.08
        }

        carbon_score = (distance * factors[vehicle]) + (electricity * 0.5)

        if carbon_score < 50:
            impact = "Low Impact 🌱"
            suggestion = "Great job! Keep using eco-friendly habits."
        elif carbon_score < 100:
            impact = "Moderate Impact ⚠️"
            suggestion = "Consider public transport and reducing electricity usage."
        else:
            impact = "High Impact 🔥"
            suggestion = "Reduce vehicle usage and switch to renewable energy sources."

        result = f"Carbon Score: {carbon_score:.2f} kg CO2 ({impact})"

    return render_template(
        'index.html',
        result=result,
        suggestion=suggestion
    )

if __name__ == '__main__':
    app.run(debug=True)