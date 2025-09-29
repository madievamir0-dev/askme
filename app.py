from flask import Flask, request, render_template
import pandas as pd
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Загружаем переменные окружения (ключи)
load_dotenv()

# Настройка Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

# Функция для загрузки и обработки базы данных товаров
def load_products():
    try:
        # Берём путь к файлу рядом с app.py
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(BASE_DIR, "products.xlsx")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл {file_path} не найден")

        # Загружаем Excel с явным указанием движка
        products = pd.read_excel(file_path, engine="openpyxl")

        # Чистим текстовые данные от пробелов и приводим к строкам
        for col in products.columns:
            if products[col].dtype == object:
                products[col] = products[col].astype(str).str.strip()

        # Проверяем нужные столбцы
        required_columns = ["name", "description", "price", "stock", "image"]
        for col in required_columns:
            if col not in products.columns:
                if col == "image":
                    products["image"] = products["name"].apply(
                        lambda x: f"{str(x).replace(' ', '_')}.jpg"
                    )
                elif col == "stock":
                    products["stock"] = 0
                else:
                    products[col] = ""

        return products

    except FileNotFoundError as fnf_error:
        print(f"[Ошибка] {fnf_error}")
        return pd.DataFrame(columns=["name", "description", "price", "stock", "image"])
    except Exception as e:
        print(f"[Ошибка загрузки Excel] {e}")
        return pd.DataFrame(columns=["name", "description", "price", "stock", "image"])

# Загружаем товары
products = load_products()

@app.route("/", methods=["GET", "POST"])
def index():
    answer = ""
    product_name = ""
    matches = []

    if request.method == "POST":
        product_name = request.form["product_name"].strip().lower()

        if not product_name:
            answer = "⚠️ Пожалуйста, введите название товара."
        elif len(product_name) > 100:
            answer = "⚠️ Название товара слишком длинное. Сократите запрос."
        else:
            # Поиск по всем столбцам с учетом регистра
            found = products[products.apply(
                lambda row: row.astype(str).str.contains(product_name, case=False, na=False).any(), axis=1)]

            if not found.empty:
                matches = found.to_dict("records")
            else:
                answer = "❌ Извините, такого товара нет в наличии."

    return render_template(
        "index.html",
        answer=answer,
        product_name=product_name,
        products=products.to_dict("records"),
        matches=matches,
    )


@app.route("/ask_more", methods=["POST"])
def ask_more():
    product_name = request.form["product_name"]
    user_question = request.form["user_question"]

    prompt = f"Ты консультант интернет-магазина. Пользователь спрашивает про товар '{product_name}'. Вопрос: {user_question}"

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        answer = response.text if response and response.text else "⚠️ Нет ответа от модели."
    except Exception as e:
        answer = f"⚠️ Ошибка при запросе к Gemini: {e}"

    return render_template(
        "index.html",
        answer=answer,
        product_name=product_name,
        products=products.to_dict("records"),
        matches=[],
    )


if __name__ == "__main__":
    app.run(debug=True)
