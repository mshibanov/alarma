import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
import requests
from bs4 import BeautifulSoup

# Включим логирование, чтобы видеть ошибки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
AUTO_START, CONTROL_METHOD, GPS_NEEDED, RESULT = range(4)

# Ваша таблица с данными (преобразована в список словарей)
PRODUCTS = [
    {"name": "Pandora DX-40R", "autostart": 0, "remote": 1, "gsm": 0, "gps": 0, "url": "https://ya7auto.ru/auto-security/car-alarms/pandora-dx-40r/"},
    {"name": "Pandora DX-40RS", "autostart": 1, "remote": 1, "gsm": 0, "gps": 0, "url": "https://ya7auto.ru/auto-security/car-alarms/pandora-dx-40rs/"},
    # ... ВСТАВЬТЕ СЮДА ВСЕ ОСТАЛЬНЫЕ УСТРОЙСТВА ИЗ ВАШЕЙ ТАБЛИЦЫ ...
    {"name": "StarLine S96 V2 LTE GPS", "autostart": 1, "remote": 0, "gsm": 1, "gps": 1, "url": "https://ya7auto.ru/auto-security/car-alarms/starline-s96-v2-lte-gps/"}
]

# Клавиатура для первого выбора
reply_keyboard_auto = [["С автозапуском", "БЕЗ автозапуска"]]
reply_keyboard_control = [["😎 Приложение в телефоне", "📺 Брелок"]]
reply_keyboard_gps = [["Да, отслеживать перемещения", "Нет, не нужно"]]

markup_auto = ReplyKeyboardMarkup(reply_keyboard_auto, one_time_keyboard=True, resize_keyboard=True)
markup_control = ReplyKeyboardMarkup(reply_keyboard_control, one_time_keyboard=True, resize_keyboard=True)
markup_gps = ReplyKeyboardMarkup(reply_keyboard_gps, one_time_keyboard=True, resize_keyboard=True)

# Функция для поиска подходящих продуктов
def find_products(autostart, remote, gps_needed):
    """
    Ищет продукты, подходящие под критерии пользователя.
    autostart: 1 - нужен, 0 - не нужен
    remote: 1 - брелок, 0 - приложение (GSM)
    gps_needed: 1 - нужен GPS, 0 - не нужен
    """
    matched_products = []
    for product in PRODUCTS:
        # Сравниваем критерии. product['gsm'] это 1 если управление через приложение (не брелок)
        if (product['autostart'] == autostart and
            product['remote'] == remote and
            product['gps'] == gps_needed):
            # Для устройств с приложением (GSM) проверяем, запрашивал ли пользователь GPS
            if remote == 0:
                if gps_needed == product['gps']:
                    matched_products.append(product)
            else:
                # Для устройств с брелоком GPS не предлагается по умолчанию в вашей таблице
                matched_products.append(product)
    return matched_products[:2]  # Возвращаем не более 2 вариантов

# Функция для получения названия и цены по URL (использует BeautifulSoup)
def fetch_product_info(url):
    """Пытается получить название и цену товара со страницы."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Проверяем, что запрос успешен

        soup = BeautifulSoup(response.text, 'html.parser')

        # Селекторы нужно подставить актуальные для вашего сайта!
        # ЭТО ПРИМЕР. ИХ НУЖНО НАСТРОИТЬ, ИСПОЛЬЗУЯ ИНСТРУМЕНТЫ РАЗРАБОТЧИКА В БРАУЗЕРЕ.
        title_selector = "h1.product-card-top__title" 
        price_selector = "span.product-card-top__price"

        title_element = soup.select_one(title_selector)
        price_element = soup.select_one(price_selector)

        title = title_element.get_text(strip=True) if title_element else "Название не найдено"
        price = price_element.get_text(strip=True) if price_element else "Цена не найдена"

        return f"{title} - {price}"

    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к {url}: {e}")
        return "Не удалось загрузить информацию о товаре."
    except Exception as e:
        logger.error(f"Ошибка при парсинге {url}: {e}")
        return "Ошибка обработки данных товара."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает опрос, задает первый вопрос."""
    user = update.message.from_user
    await update.message.reply_text(
        f"👋🏻 Приветствуем, {user.first_name}!\n\n"
        "Готов помочь подобрать идеальную систему для твоего автомобиля!\n\n"
        "🦾 Давай определимся с ключевыми функциями\n\n"
        "☀️ Подавляющее большинство наших клиентов выбирают систему с главной целью — реализовать дистанционный запуск двигателя.\n\n"
        "В нашем климате прогрев двигателя перед поездкой — это необходимость. Даже при небольшом минусе это значительно снижает износ мотора.\n\n"
        "Ну и конечно, садиться в уже тёплый и комфортный салон — это просто приятно.\n\n"
        "Какая функция для вас в приоритете?",
        reply_markup=markup_auto
    )
    return AUTO_START

async def auto_start_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор автозапуска и задает второй вопрос."""
    user_choice = update.message.text
    context.user_data['autostart'] = 1 if user_choice == "С автозапуском" else 0

    await update.message.reply_text(
        "📡 Теперь давай выберем способ управления\n\n"
        "🙄 Есть устаревший метод — управление с брелока сигнализации. Его минус в нестабильном сигнале: есть риск не получить оповещение о тревоге. Поэтому мы рекомендуем более современный вариант — управление со смартфона.\n\n"
        "☺️ Через мобильное приложение ты сможешь дистанционно открывать и закрывать авто, отслеживать его местоположение и статус, настраивать датчики и многое другое. Главное — ты гарантированно получишь пуш-уведомление о любом происшествии, где бы ты ни был.\n\n"
        "Как вам удобнее управлять системом?",
        reply_markup=markup_control
    )
    return CONTROL_METHOD

async def control_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор способа управления и задает третий вопрос."""
    user_choice = update.message.text
    # Если выбрано приложение, то remote=0 (брелок не нужен), и наоборот.
    context.user_data['remote'] = 1 if user_choice == "📺 Брелок" else 0

    # Если пользователь выбрал управление через приложение, спросим про GPS.
    if context.user_data['remote'] == 0:
        await update.message.reply_text(
            "🔥 Отлично! Мы почти подобрали твою идеальную систему. Остался последний шаг.\n\n"
            "Если ты часто передаешь ключи другим людям или тебе критично важно отслеживать каждое перемещение автомобиля, то тебе нужна система со встроенным GPS-модулем.\n\n"
            "Он позволит тебе в реальном времени видеть точное местоположение машины, а в приложении можно будет посмотреть детальный маршрут ее поездки.\n\n"
            "Нужна ли функция GPS-отслеживания?",
            reply_markup=markup_gps
        )
        return GPS_NEEDED
    else:
        # Если выбран брелок, GPS не предлагаем (согласно таблице)
        context.user_data['gps'] = 0
        return await show_results(update, context)

async def gps_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор необходимости GPS."""
    user_choice = update.message.text
    context.user_data['gps'] = 1 if user_choice == "Да, отслеживать перемещения" else 0
    return await show_results(update, context)

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ищет подходящие продукты и показывает результаты пользователю."""
    user_data = context.user_data
    autostart = user_data.get('autostart', 0)
    remote = user_data.get('remote', 0)
    gps = user_data.get('gps', 0)

    recommended_products = find_products(autostart, remote, gps)

    if not recommended_products:
        await update.message.reply_text("К сожалению, по вашим критериям не найдено подходящих систем. Попробуйте изменить параметры поиска.")
        return ConversationHandler.END

    message_text = "Вот подходящие для вас варианты:\n\n"
    for product in recommended_products:
        # Пытаемся получить актуальную информацию о товаре
        product_info = fetch_product_info(product['url'])
        message_text += f"• <a href='{product['url']}'>{product['name']}</a>\n{product_info}\n\n"

    message_text += (
        "\nДля получения консультации и оформления заказа, пожалуйста, оставьте ваш номер телефона. "
        "Наш специалист свяжется с вами в ближайшее время.\n\n"
        "👇 Нажмите на кнопку ниже, чтобы отправить номер."
    )

    # Создаем клавиатуру с кнопкой для отправки номера
    contact_keyboard = [[KeyboardButton("📞 Отправить номер телефона", request_contact=True)]]
    contact_markup = ReplyKeyboardMarkup(contact_keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(message_text, reply_markup=contact_markup, parse_mode='HTML')
    return RESULT

async def received_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает полученный контакт и отправляет данные в CRM."""
    phone_number = update.message.contact.phone_number
    # Форматируем номер (убираем плюс для формы)
    formatted_phone = phone_number.lstrip('+')

    # Данные для отправки в форму CRM
    form_data = {
        'Телефон': formatted_phone
    }

    try:
        # Отправляем POST-запрос на URL вашей формы
        response = requests.post('https://ya7auto.ru/crm/form/iframe/4/', data=form_data)
        if response.status_code == 200:
            await update.message.reply_text(
                "✅ Спасибо! Ваш номер принят. Мы уже обрабатываем заявку, и наш специалист скоро с вами свяжется. Хорошего дня!",
                reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)  # Убираем клавиатуру
            )
        else:
            await update.message.reply_text("Произошла ошибка при отправке номера. Пожалуйста, попробуйте позже.")
    except requests.RequestException:
        await update.message.reply_text("Не удалось соединиться с сервером. Пожалуйста, попробуйте позже.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершает диалог."""
    await update.message.reply_text('Диалог прерван. Если понадобится помощь — просто напишите /start.')
    return ConversationHandler.END

def main() -> None:
    """Запускает бота."""
    # Замените 'YOUR_BOT_TOKEN' на токен, полученный от @BotFather
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AUTO_START: [MessageHandler(filters.Regex("^(С автозапуском|БЕЗ автозапуска)$"), auto_start_choice)],
            CONTROL_METHOD: [MessageHandler(filters.Regex("^(😎 Приложение в телефоне|📺 Брелок)$"), control_method_choice)],
            GPS_NEEDED: [MessageHandler(filters.Regex("^(Да, отслеживать перемещения|Нет, не нужно)$"), gps_choice)],
            RESULT: [MessageHandler(filters.CONTACT, received_contact)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Запуск бота в режиме polling
    application.run_polling()

if __name__ == '__main__':
    main()