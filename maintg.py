import asyncio

from random import randint, choice
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from decouple import config

from models import User, Support

API_TOKEN = config('TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


class UserSupport(StatesGroup):
    message = State()
    dialog = State()



mainmenu = InlineKeyboardBuilder()
mainmenu.row(types.InlineKeyboardButton(text = '🎲 Рандомне число', callback_data='random'))
mainmenu.row(types.InlineKeyboardButton(text = '🆘 Допомога', callback_data='help'))

back_mainmenu = InlineKeyboardBuilder()
back_mainmenu_button = types.InlineKeyboardButton(text = '⬅ Назад головне меню', callback_data='back_mainmenu')
back_mainmenu.row(back_mainmenu_button)






@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user = User.get_or_none(id=message.from_user.id)
    if user:
        await message.answer('Вітаю ще раз', reply_markup=mainmenu.as_markup())
    else:
        User.create(id=message.from_user.id, full_name=message.from_user.full_name)
        await message.answer('Вітаю, ви зареєструвались', reply_markup=mainmenu.as_markup())
    
@dp.callback_query(F.data == "back_mainmenu")
async def back_mainmenu2(call: types.CallbackQuery):
    await call.message.edit_text('Головне меню', reply_markup=mainmenu.as_markup())
    
@dp.callback_query(F.data == "random")
async def random(call: types.CallbackQuery):
    await call.message.edit_text(f'Рандомне число: {randint(0, 100)}', reply_markup=back_mainmenu.as_markup())


@dp.message(Command('admin'))
async def cmd_admin(message: types.Message, command: CommandObject):
    user = User.get_or_none(id=message.from_user.id)
    if not user:
        return
    password = '123456'
    args = command.args
    if password == args:
        if user.is_admin:
            await message.answer('Ви вже адміністратор')
        else:
            user.is_admin = True
            user.save()
            await message.answer('Ви стали адміністратором')
    
@dp.message(Command('admin_clear'))
async def cmd_admin_clear(message: types.Message):
    user = User.get_or_none(id=message.from_user.id)
    if not user:
        return
    if not user.is_admin:
        return
    admins = User.filter(is_admin=True)
    for admin in admins:
        admin.is_admin = False
        admin.save()
    await message.answer('Видалено всіх адміністраторів')



@dp.callback_query(F.data == "help")
async def help(call: types.CallbackQuery, state: FSMContext):
    await state.set_state( UserSupport.message )
    await call.message.edit_text('Напишіть ваше запитання або проблему. Менеджер зв\'яжеться з вами найближчим часом')
    
@dp.message(UserSupport.message)
async def message_form_user(message: types.Message, state: FSMContext):
    admins = User.filter(is_admin=True)
    admin = choice(admins)
    support = Support.create(user=message.from_user.id, admin=admin.id, text=message.text)

    await message.answer(f'Ваше повідомлення буде опрацьовано найближчим часом. До вас прикріплений менеджер {admin.full_name}')
    await state.set_state( UserSupport.dialog )
    await state.update_data(support_id=support.id, admin_id=admin.id, client_id=message.from_user.id)
    
    #Повідомлення адміну
    answer = InlineKeyboardBuilder()
    answer.row(types.InlineKeyboardButton(text = 'Відповісти', callback_data=f'support_answer_{support.id}'))
    await bot.send_message(admin.id, f'Нове повідомлення від користувача {message.from_user.full_name}', reply_markup=answer.as_markup())

@dp.callback_query(F.data.startswith("support_answer_"))
async def support_answer(call: types.CallbackQuery, state: FSMContext):
    support_id = call.data.split('_')[-1]
    support = Support.get_or_none(id=support_id)
    if not support:
        await call.message.edit_text('Повідомлення не знайдено, можливо воно було видалено')
        return
    await state.set_state( UserSupport.dialog )
    await state.update_data(support_id=support.id, admin_id=support.admin.id, client_id=support.user.id)
    await call.message.answer(f'Відповідь на повідомлення від {support.user.full_name}:\n{support.text}')
    await call.message.answer('Напишіть відповідь на повідомлення')
    
    #Повідомлення користувачу
    await bot.send_message(support.user.id, 'Менеджер підключився до діалогу')


@dp.message(UserSupport.dialog)
async def support_dialog(message: types.Message, state: FSMContext):
    data = await state.get_data()
    support_id = data.get('support_id')
    admin_id = data.get('admin_id')
    client_id = data.get('client_id')
    support = Support.get_or_none(id=support_id)
    if not support or support.is_closed:
        await message.answer('Запит не знайдено, можливо воно було видалено або завершено')
        return
    
    print(f'message from {message.from_user.id} msg: {message.text}')
    print(f'admin: {admin_id}', f'client: {client_id}', f'support _admin: {support.admin.id}')
    
    exit_markup = InlineKeyboardBuilder()
    exit_markup.row(types.InlineKeyboardButton(text = 'Завершити діалог', callback_data=f'support_exit'))
    
    if message.from_user.id == admin_id:
        await bot.copy_message(client_id, message.chat.id, message.message_id, reply_markup=exit_markup.as_markup())
    else:
        await bot.copy_message(admin_id, message.chat.id, message.message_id, reply_markup=exit_markup.as_markup())

@dp.callback_query(F.data.startswith("support_exit"))
async def support_exit(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    support_id = data.get('support_id')
    support = Support.get_or_none(id=support_id)
    if not support:
        await call.message.edit_text('Повідомлення не знайдено, можливо воно було видалено')
        return
    
    support.is_closed = True
    support.save()
    
    сlose_markup = InlineKeyboardBuilder()
    сlose_markup.row(types.InlineKeyboardButton(text = '⬅ Назад головне меню', callback_data=f'support_close'))
    
    await bot.send_message(support.user.id, 'Діалог завершено', reply_markup=сlose_markup.as_markup())
    await bot.send_message(support.admin.id, 'Діалог завершено', reply_markup=сlose_markup.as_markup())

@dp.callback_query(F.data == "support_close", UserSupport.dialog)
async def support_close(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text('Головне меню', reply_markup=mainmenu.as_markup())


if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot, skip_updates=True))