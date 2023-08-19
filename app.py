import os
import requests

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///foodies.db")

# SET API_KEY HERE
api_key = "SET API_KEY HERE"

# Make sure API key is set
if not api_key:
    raise RuntimeError("API_KEY not set")

url = "https://spoonacular-recipe-food-nutrition-v1.p.rapidapi.com/"

headers = {
    'x-rapidapi-host': "spoonacular-recipe-food-nutrition-v1.p.rapidapi.com",
    'x-rapidapi-key': f"{api_key}"
}


################ Dictionaries ################

meal_type = {
    'breakfast': 'Breakfast',
    'main course': 'Main Course',
    'dessert': 'Dessert',
}

cuisine_type = {
    'african': 'African',
    'american': 'American',
    'british': 'British',
    'caribbean': 'Caribbean',
    'chinese': 'Chinese',
    'french': 'French',
    'german': 'German',
    'greek': 'Greek',
    'indian': 'Indian',
    'irish': 'Irish',
    'italian': 'Italian',
    'japanese': 'Japanese',
    'jewish': 'Jewish',
    'korean': 'Korean',
    'latin_american': 'Latin American',
    'mediterranean': 'Mediterranean',
    'mexican': 'Mexican',
    'nordic': 'Nordic',
    'spanish': 'Spanish',
    'thai': 'Thaï',
    'vietnamese': 'Vietnamese',
}

diet_type = {
    'gluten_free': 'Gluten Free',
    'vegetarian': 'Vegetarian',
    'vegan': 'Vegan',
}

################ Dictionaries ################


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Main page"""

    # Pick username in database to print it in main page
    row = db.execute("SELECT username FROM users WHERE id = ?",
                     session["user_id"])

    return render_template("index.html", name=row[0]['username'], meal_type=meal_type, cuisine_type=cuisine_type, diet_type=diet_type)


@app.route("/recipes", methods=["GET", "POST"])
@login_required
def get_recipes():
    """Show recipes results"""

    query = []
    meal = []
    cuisine = []
    diet = []

    if request.method == "POST":

        # Store "What's in tour fridge?" user input
        query = str(request.form.get("query")).strip()

        if not query:
            flash("Please enter ingredient(s) or query")
            return redirect("/")

        # Store meal type
        meal = request.form.getlist("meal_type")

        # Store cuisine type
        cuisine = request.form.getlist("cuisine_type")

        # Store diet type
        diet = request.form.getlist("diet_type")

        search = "recipes/search"

        # "query": query, "cuisine":cuisine, "type":meal_type, "diet": diet}
        querystring = {"number": "12", "query": query,
                       "cuisine": cuisine, "type": meal, "diet": diet}
        response = requests.request(
            "GET", url + search, headers=headers, params=querystring).json()
        response = response['results']
        print(response)

        data_recipes = []

        for i in range(len(response)):
            data_recipes.append(response[i])

            steps = get_steps(response[i]['id'])
            ingredients = get_ingredients(response[i]['id'])

            data_recipes[i]['steps'] = steps
            data_recipes[i]['ingredient_image'] = ingredients[0]
            data_recipes[i]['ingredient_metric'] = ingredients[1]

        return render_template("recipes.html", recipes=data_recipes)

    return render_template("recipes.html")


def get_steps(recipe_id):
    """Get steps from recipe"""

    search = "recipes/{0}/analyzedInstructions".format(str(recipe_id))

    querystring = {"stepBreakdown": "true"}

    step = []

    response_step = requests.request(
        "GET", url + search, headers=headers, params=querystring).json()

    # Checking if there is data
    if len(response_step) != 0:

        response_step = response_step[0]["steps"]

        for i in range(len(response_step)):
            if len(response_step[i]["step"]) != 0:
                step.append(response_step[i]["step"])

    return step


def get_ingredients(recipe_id):
    """Get ingredients from recipe"""

    search = "recipes/{0}/ingredientWidget.json".format(str(recipe_id))

    ingredient_image = []
    ingredient_metric = []

    response_ingredients = requests.request(
        "GET", url + search, headers=headers).json()
    response_ingredients = response_ingredients['ingredients']

    # Checking if there is data
    if len(response_ingredients) != 0:

        for i in range(len(response_ingredients)):
            if len(response_ingredients) != 0:

                ingredient_image.append(response_ingredients[i]['image'])

                response_amount = response_ingredients[i]['amount']
                response_amount = response_amount['us']

                ingredient_metric.append(str(
                    response_amount['value']) + " " + response_amount['unit'] + " of " + response_ingredients[i]['name'])

    return ingredient_image, ingredient_metric


@app.route("/save", methods=["GET", "POST"])
def save():
    """Save recipe in database"""

    # Select all saved recipes if there is
    recipes = db.execute(
        "SELECT * FROM recipes WHERE id = ?", session["user_id"])

    # Get recipe id that user wants to save
    recipe_id = int(request.form.get("save"))

    # Check if this recipe is already saved
    for row in recipes:
        if row["recipe_id"] == recipe_id:
            flash('This recipe is already saved !')
            return get_recipes()

    #  If not save it into database
    db.execute("INSERT INTO recipes (id, recipe_id) VALUES (?, ?)",
               session["user_id"], recipe_id)
    flash('Recipe has been saved !')

    return my_recipes()


@app.route("/remove", methods=["GET", "POST"])
def remove():
    """Remove recipe from database"""

    # Get recipe id that user wants to remove
    recipe_id = int(request.form.get("remove"))

    db.execute("DELETE FROM recipes WHERE id = ? AND recipe_id = ?",
               session["user_id"], recipe_id)
    flash('Recipe has been removed !')

    return my_recipes()


@app.route("/saved", methods=["GET", "POST"])
def my_recipes():
    """Print saved recipes"""

    # Get all saved recipes from database
    my_recipes = db.execute(
        "SELECT recipe_id FROM recipes WHERE id = ?", session['user_id'])

    search = "recipes/informationBulk"

    # List of saved recipes
    saved_recipes = []

    for i in range(len(my_recipes)):

        # Dict of each recipes
        recipe = {}

        # variable that store each recipe id
        recipe_id = my_recipes[i]["recipe_id"]

        querystring = {"ids": recipe_id}

        response = requests.request(
            "GET", url+search, headers=headers, params=querystring).json()

        response_sum = response
        response_sum = response_sum[0]

        recipe['id'] = recipe_id
        recipe['title'] = response_sum['title']
        recipe['readyInMinutes'] = response_sum['readyInMinutes']
        recipe['servings'] = response_sum['servings']
        recipe['sourceUrl'] = response_sum['sourceUrl']
        recipe['image'] = response_sum['image']

        steps = get_steps(recipe_id)
        ingredients = get_ingredients(recipe_id)

        recipe['steps'] = steps
        recipe['ingredient_image'] = ingredients[0]
        recipe['ingredient_metric'] = ingredients[1]

        saved_recipes.append(recipe)

    return render_template("my_recipes.html", recipes_saved=saved_recipes)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Please enter your username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Please enter your password")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password")
            return render_template("login.html")
        else:

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Username is missing")
            return render_template("register.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Password is missing")
            return render_template("register.html")

        # Ensure password match
        if request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords don't match")
            return render_template("register.html")
        else:

            # store username and password has into variables
            username = request.form.get("username")
            hash = generate_password_hash(request.form.get("confirmation"))

        # if everything is good then store user info into database
        try:
            db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
            return redirect("/")
        except:
            # return apology if username is already taken
            flash("Username already taken")
            return render_template("register.html")

    else:
        return render_template("register.html")


@app.route("/set_password", methods=["GET", "POST"])
@login_required
def set_password():
    """Allow user to change password"""

    if request.method == "POST":

        # Select user row
        user_row = db.execute(
            "SELECT * FROM users WHERE id = ?", session["user_id"])

        # Ensure old password was submitted
        if not request.form.get("old_password") or not check_password_hash(user_row[0]["hash"], request.form.get("old_password")):
            flash("Invalid old password")
            return render_template("set_password.html")

        # Ensure new password was submitted
        if not request.form.get("new_password"):
            flash("Please provide new password")
            return render_template("set_password.html")

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            flash("Please confirme new password")
            return render_template("set_password.html")

        # Ensure new password match
        if request.form.get("new_password") != request.form.get("confirmation"):
            flash("New passwords don't match")
            return render_template("set_password.html")
        else:
            # HASH new password
            hash = generate_password_hash(request.form.get("confirmation"))
            # UPDATE new password in database
            db.execute("UPDATE users SET hash = ? WHERE id = ?",
                       hash, session["user_id"])
            flash("New password has been set")

            return redirect("/")

    return render_template("set_password.html")