from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from bson import ObjectId  # Import ObjectId
import os

app = Flask(__name__)

# MongoDB connection setup
client = MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"]
users_collection = db["users"]
cart_collection = db["cart"]

# Define the folder where uploaded product images will be stored
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure a secret key for session management
# Replace with a strong, random secret key
app.secret_key = '123'


@app.route('/')
def login_selection():
    return render_template('login_selection.html')


@app.route('/redirect_login', methods=['POST'])
def redirect_login():
    role = request.form['role']
    if role == 'admin':
        return redirect(url_for('admin_login'))
    elif role == 'customer':
        return redirect(url_for('customer_login'))
    else:
        return "Invalid role selected."


@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')


@app.route('/signup_admin', methods=['GET', 'POST'])
def signup_admin():
    if request.method == 'POST':
        username = request.form['username']
        role = 'admin'

        existing_user = users_collection.find_one(
            {"username": username, "role": "admin"})

        if existing_user:
            return "User already exists"
        else:
            new_user = {"username": username, "role": 'admin'}
            users_collection.insert_one(new_user)
            return "Admin sign-up successful"

    return render_template('signup_admin.html')


@app.route('/customer_login')
def customer_login():
    return render_template('customer_login.html')


@app.route('/signup_customer', methods=['GET', 'POST'])
def signup_customer():
    if request.method == 'POST':
        username = request.form['username']
        role = 'customer'

        existing_user = users_collection.find_one(
            {"username": username, "role": 'customer'})

        if existing_user:
            return "User already exists"
        else:
            new_user = {"username": username, "role": 'customer'}
            users_collection.insert_one(new_user)
            return "Customer sign-up successful"

    return render_template('signup_customer.html')


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']

        user = users_collection.find_one({"username": username, "role": role})

        if user:
            # Store user details in session
            session['username'] = username
            session['role'] = role

            if role == "admin":
                return redirect(url_for('admin_home'))
            else:
                return redirect(url_for('customer_home'))
        else:
            return "Login failed"

    return render_template('login.html')


@app.route('/admin_home')
def admin_home():
    # Check if the user is logged in
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # Retrieve the list of customers from the database
    customers = users_collection.find({"role": "customer"})

    return render_template('admin_home.html', users=customers)


@app.route('/manage_product', methods=['GET', 'POST'])
def manage_product():
    if request.method == 'GET':
        # Add your code to retrieve and display products
        products = db.products.find()
        return render_template('manage_product.html', products=products)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'delete':
            # Perform deletion logic using the product ID
            product_id = request.form.get('product_id')
            db.products.delete_one({"_id": ObjectId(product_id)})
            # Redirect to the product management page or render a refreshed view
            return redirect(url_for('manage_product'))

        if action == 'update':
            # Perform update logic using the product ID and form data
            product_id = request.form.get('product_id')
            updated_product_data = {
                "name": request.form['updated_product_name'],
                "quantity": int(request.form['updated_quantity']),
                "price": float(request.form['updated_price']),
                "category": request.form['updated_category'],
                # Update image path or handle new image upload
            }
            db.products.update_one({"_id": ObjectId(product_id)}, {
                                   "$set": updated_product_data})
            # Redirect to the product management page or render a refreshed view
            return redirect(url_for('manage_product'))

    return render_template('manage_product.html')


@app.route('/customer_home')
def customer_home():
    if 'username' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    # Retrieve product information from the database
    products = db.products.find()

    # Fetch the items in the user's cart
    username = session['username']
    cart_items = cart_collection.find({"username": username})

    return render_template('customer_home.html', products=products, cart_items=cart_items)


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))


@app.route('/add_product', methods=['POST'])
def add_product():
    # Check if the user is logged in as an admin
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        product_name = request.form['product_name']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        category = request.form['category']

        # Handle image file upload
        if 'image' in request.files:
            image_file = request.files['image']

            if image_file.filename != '':
                # Secure the filename to prevent path traversal
                filename = secure_filename(image_file.filename)
                # Save the image to the specified folder
                image_path = os.path.join(
                    app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
            else:
                # Provide a default image path if no image is uploaded
                image_path = 'static/images/default.jpg'

            # Add the product to the database
            product = {
                "name": product_name,
                "quantity": quantity,
                "price": price,
                "category": category,
                "image": image_path
            }
            db.products.insert_one(product)

    return redirect(url_for('admin_home'))


@app.route('/search_products', methods=['POST'])
def search_products():
    if request.method == 'POST':
        search_query = request.form['search_query']

        # Assuming you have a 'products' collection in your database
        # Modify the query based on your data model
        search_results = db.products.find(
            {"name": {"$regex": f".*{search_query}.*", "$options": 'i'}})

        # Convert MongoDB cursor to list of dictionaries for JSON serialization
        results_list = list(search_results)
        return jsonify(results_list)

# ... (existing code)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'username' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        product_name = request.form['product_name']
        product_price = float(request.form['product_price'])
        username = session['username']

        # Check if the product is already in the cart for the user
        existing_item = cart_collection.find_one({
            "username": username,
            "product_name": product_name
        })

        if existing_item:
            # If the product is already in the cart, update the quantity
            cart_collection.update_one(
                {"_id": existing_item["_id"]},
                {"$inc": {"quantity": 1}}
            )
        else:
            # If the product is not in the cart, add it
            cart_item = {
                "username": username,
                "product_name": product_name,
                "quantity": 1,
                "price": product_price
            }
            cart_collection.insert_one(cart_item)

    return ('', 204)

# ... (existing code)


@app.route('/decrement_or_remove_from_cart', methods=['POST'])
def decrement_or_remove_from_cart():
    if 'username' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        product_id = request.form['product_id']
        username = session['username']

        # Find the item in the cart
        cart_item = cart_collection.find_one(
            {"_id": ObjectId(product_id), "username": username}
        )

        if cart_item:
            # If the quantity is greater than 1, decrement it; otherwise, remove the item
            if cart_item['quantity'] > 1:
                cart_collection.update_one(
                    {"_id": ObjectId(product_id)},
                    {"$inc": {"quantity": -1}}
                )
            else:
                cart_collection.delete_one(
                    {"_id": ObjectId(product_id), "username": username}
                )

    return ('', 204)


@app.route('/view_cart')
def view_cart():
    if 'username' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    username = session['username']
    cart_items = cart_collection.find({"username": username})

    return render_template('cart.html', cart_items=cart_items)
# ... (existing code)


@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        # Get the current logged-in user's username
        customer_name = session.get('username', 'Anonymous')

        # Retrieve the cart items from the cart collection
        cart_items = cart_collection.find({"username": customer_name})

        # Extract order details from the cart items
        order_details = []
        total_checkout_price = 0  # Initialize total checkout price

        for cart_item in cart_items:
            order_details.append({
                "product_name": cart_item["product_name"],
                "quantity": cart_item["quantity"],
            })

            # Calculate and update the total checkout price
            total_checkout_price += cart_item["price"] * cart_item["quantity"]

        # If order_details are provided in the request, use them instead
        if request.json and "order_details" in request.json:
            order_details = request.json["order_details"]

            # Recalculate the total checkout price based on the provided order details
            total_checkout_price = sum(
                item["quantity"] * item["price"] for item in order_details
            )

        # Check if the customer already has an existing order
        existing_order = db.orders.find_one({"customer_name": customer_name})

        if existing_order:
            # If an existing order is found, update the order details and total checkout price
            db.orders.update_one(
                {"customer_name": customer_name},
                {
                    "$push": {
                        "order_details": {"$each": order_details}
                    },
                    "$inc": {"total_checkout_price": total_checkout_price}
                }
            )
        else:
            # If no existing order is found, create a new order
            new_order = {
                "customer_name": customer_name,
                "order_details": order_details,
                "total_checkout_price": total_checkout_price
            }
            db.orders.insert_one(new_order)

        # Clear the user's cart after checkout
        cart_collection.delete_many({"username": customer_name})

        return jsonify({'message': 'Order placed successfully!'})
    except Exception as e:
        print(str(e))
        return jsonify({'error': 'Error during checkout. Please try again.'}), 500


@app.route('/admin_orders')
def admin_orders():
    # Check if the user is logged in
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # Retrieve all orders from the orders collection
    orders = db.orders.find()

    return render_template('admin_orders.html', orders=orders)


@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        customer_name = request.form['customer_name']
        order_id = request.form['order_id']

        # Retrieve the order details
        order = db.orders.find_one({"_id": ObjectId(order_id)})

        if order:
            # Decrease product quantities
            for item in order.get('order_details', []):
                product_name = item.get('product_name')
                quantity = item.get('quantity')
                update_product_quantity(product_name, quantity)

            # Store the placed order details in "placed_orders" collection
            db.placed_orders.insert_one(order)

            # Remove the placed order from the "orders" collection
            db.orders.delete_one({"_id": ObjectId(order_id)})

            return jsonify({'message': 'Order placed successfully!'})
        else:
            return jsonify({'error': 'Order not found.'}), 404

    except Exception as e:
        print(str(e))
        return jsonify({'error': 'Error placing order. Please try again.'}), 500


def update_product_quantity(product_name, quantity):
    # Add logic to update product quantity in your products collection
    # Example:
    db.products.update_one({"name": product_name}, {
                           "$inc": {"quantity": -quantity}})
    pass


@app.route('/customer_details')
def customer_details():
    # Retrieve customer users from the MongoDB collection
    customer_users = users_collection.find({"role": "customer"})

    # Pass the customer users data to the template
    return render_template('customer_details.html', users=customer_users)


@app.route('/placed_orders')
def placed_orders():
    # Check if the user is logged in
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    # Retrieve all placed orders from the placed_orders collection
    placed_orders = db.placed_orders.find()

    return render_template('placed_orders.html', orders=placed_orders)


if __name__ == '__main__':
    app.run(debug=True)
