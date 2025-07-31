import random
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS # Import CORS to handle cross-origin requests
from menu_data import menu_data # Import menu_data from the separate file

app = Flask(__name__)
CORS(app) # Enable CORS for all routes in your Flask app.

# Define keywords for common allergens
# This dictionary maps the allergen name (from frontend) to a list of ingredient keywords
ALLERGEN_KEYWORDS = {
    "telur": ["Telur", "Mayonnaise"], # 'Telur' covers 'Telur Ayam' too
    "kacang": ["Kacang", "Saus Kacang"], # 'Kacang' covers 'Kacang Tanah' too
    # Add more allergens and their associated ingredients here as needed
    # e.g., "susu": ["Susu", "Keju", "Mentega"],
    # e.g., "gandum": ["Tepung Terigu", "Roti"],
}

@app.route('/')
def index():
    """Renders the main HTML page for the web application."""
    return render_template('index.html')

@app.route('/plan_meals', methods=['POST'])
def plan_meals():
    """
    Handles the meal planning request from the frontend.
    It filters menus based on allergens, generates a daily meal plan,
    and compiles a shopping list.
    """
    try:
        data = request.get_json()
        days = int(data.get('days'))
        portions = int(data.get('portions'))
        selected_allergens = data.get('allergens', []) # Renamed for clarity

        if not (3 <= days <= 7):
            return jsonify({"error": "Days must be 3 or 7."}), 400
        if portions <= 0:
            return jsonify({"error": "Portions must be a positive number."}), 400

        # --- Dynamic Allergen Filtering Logic ---
        # This function checks if a menu item contains any of the selected allergens
        def contains_allergen(menu_item, selected_allergens_list):
            for allergen in selected_allergens_list:
                keywords = ALLERGEN_KEYWORDS.get(allergen.lower()) # Get keywords for the selected allergen
                if keywords:
                    for ingredient_name in menu_item['ingredients'].keys():
                        # Check if any part of the ingredient name matches an allergen keyword (case-insensitive)
                        if any(keyword.lower() in ingredient_name.lower() for keyword in keywords):
                            return True # This menu item contains a selected allergen
            return False # No selected allergens found in this menu item

        # Filter menus based on selected allergens using the new logic
        allergen_free_menus = [
            menu for menu in menu_data
            if not contains_allergen(menu, selected_allergens)
        ]
        # --- End Dynamic Allergen Filtering Logic ---

        # Separate filtered menus by category
        master_lauk_menus = [m for m in allergen_free_menus if m['category'] == 'lauk']
        master_sayur_menus = [m for m in allergen_free_menus if m['category'] == 'sayur']
        master_buah_menus = [m for m in allergen_free_menus if m['category'] == 'buah']

        # Check if we have enough options in each category for 2 meals (lunch, dinner)
        if len(master_lauk_menus) < 2:
            return jsonify({"error": "Not enough 'lauk' (main dish) menus available after filtering for allergens to create 2 meals per day. Please adjust your allergen selection or add more 'lauk' options."}), 400
        if len(master_sayur_menus) < 2:
            return jsonify({"error": "Not enough 'sayur' (vegetable) menus available after filtering for allergens to create 2 meals per day. Please adjust your allergen selection or add more 'sayur' options."}), 400
        if len(master_buah_menus) < 2:
            return jsonify({"error": "Not enough 'buah' (fruit) menus available after filtering for allergens to create 2 meals per day. Please adjust your allergen selection or add more 'buah' options."}), 400

        meal_plan = []
        shopping_list_grams = {} # Stores aggregated ingredients in grams

        for day in range(days):
            daily_meals = {
                "day": day + 1,
                "lunch": [],
                "dinner": []
            }

            # Function to pick a complete meal set from available categories
            # This version picks randomly from the master lists, allowing repetition within a day.
            def pick_complete_meal_set():
                try:
                    chosen_lauk = random.choice(master_lauk_menus)
                    chosen_sayur = random.choice(master_sayur_menus)
                    chosen_buah = random.choice(master_buah_menus)
                    return [chosen_lauk, chosen_sayur, chosen_buah]
                except IndexError:
                    raise ValueError("Not enough unique menus in all categories for meal generation. Consider adding more options.")

            try:
                # Assign complete meal sets to each slot (only lunch and dinner now)
                lunch_set = pick_complete_meal_set()
                dinner_set = pick_complete_meal_set()

                daily_meals["lunch"] = [item['name'] for item in lunch_set]
                daily_meals["dinner"] = [item['name'] for item in dinner_set]

                # Add ingredients to shopping list (in grams)
                for meal_set in [lunch_set, dinner_set]: # Only iterate over lunch and dinner sets
                    for chosen_menu_item in meal_set:
                        for ingredient, weight in chosen_menu_item['ingredients'].items():
                            shopping_list_grams[ingredient] = shopping_list_grams.get(ingredient, 0) + (weight * portions)

            except ValueError as ve:
                return jsonify({"error": str(ve)}), 400
            except Exception as e:
                return jsonify({"error": f"An unexpected error occurred during meal selection: {str(e)}"}), 500

            meal_plan.append(daily_meals)

        # Return the aggregated shopping list in grams directly
        formatted_shopping_list = {
            item: f"{value} g" for item, value in shopping_list_grams.items()
        }

        return jsonify({
            "meal_plan": meal_plan,
            "shopping_list": formatted_shopping_list
        })

    except ValueError:
        return jsonify({"error": "Invalid input for days or portions. Please enter numbers."}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred on the server: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
