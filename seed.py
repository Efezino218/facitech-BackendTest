"""
ISCOOA Facitech — Seed Data Script
Run with: python manage.py shell < seed.py
Creates the ISCOOA association, config and initial accounts.
"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from associations.models import Association, AssociationConfig
from accounts.models import User


print('Creating ISCOOA association...')
association = Association.objects.create(
    name        = 'ISCOOA — Ikota Shopping Complex Owners and Operators Association',
    slug        = 'iscooa',
    short_name  = 'ISCOOA',
    location    = 'Ikota Shopping Complex, VGC, Lagos',
    is_active   = True,
)

print('Creating ISCOOA association config...')
config = AssociationConfig.objects.create(
    association           = association,
    member_prefix         = 'ISCOOA',
    subscription_rate     = 100000,    # ₦1,000 per shop per month
    bot_threshold         = 500000000, # ₦5,000,000
    association_share     = 20,        # 20% to ISCOOA
    platform_share        = 80,        # 80% to Iprolance
    primary_color         = '#1a3a5c', # Navy
    secondary_color       = '#c9a84c', # Gold
    contact_email         = 'secretariat@iscooa.ng',
    contact_phone         = '+234-1-234-5678',
    footer_text           = 'Powered by Cool Microfinance Bank · Developed by Iprolance LLC',
    wallet_provider       = 'Cool Microfinance Bank',
    wallet_provider_short = 'Cool MFB',
    toilet_association_share = 100,
)

print('Creating Iprolance Super Admin...')
superadmin = User.objects.create_user(
    email       = 'admin@iprolance.ng',
    password    = 'iproadmin',
    first_name  = 'Iprolance',
    last_name   = 'Admin',
    role        = 'sa',
    is_staff    = True,
    is_superuser = True,
)

print('Creating ISCOOA President...')
president = User.objects.create_user(
    email       = 'pres@iscooa.ng',
    password    = 'pres2026',
    first_name  = 'Emeka',
    last_name   = 'Okafor',
    role        = 'is',
    ipos        = 'president',
    association = association,
)

print('Creating ISCOOA Treasurer...')
treasurer = User.objects.create_user(
    email       = 'tres@iscooa.ng',
    password    = 'tres2026',
    first_name  = 'Adaeze',
    last_name   = 'Okonkwo',
    role        = 'is',
    ipos        = 'treasurer',
    association = association,
)

print('Creating ISCOOA Secretary General...')
secretary = User.objects.create_user(
    email       = 'sec@iscooa.ng',
    password    = 'sec2026',
    first_name  = 'Funmi',
    last_name   = 'Adeleke',
    role        = 'is',
    ipos        = 'secretary_general',
    association = association,
)

print('Creating BOT Chairman...')
bot_chairman = User.objects.create_user(
    email       = 'bot.chairman@iscooa.ng',
    password    = 'bot2026',
    first_name  = 'Rotimi',
    last_name   = 'Adeyemi',
    role        = 'bot',
    association = association,
)

print('Creating BOT Member...')
bot_member = User.objects.create_user(
    email       = 'bot.member@iscooa.ng',
    password    = 'bot2026',
    first_name  = 'Ngozi',
    last_name   = 'Okonkwo',
    role        = 'bot',
    association = association,
)

print('Creating Legal Adviser...')
adviser = User.objects.create_user(
    email       = 'adv@iscooa.ng',
    password    = 'adv2026',
    first_name  = 'Chioma',
    last_name   = 'Nwachukwu',
    role        = 'adv',
    association = association,
)

print('Creating test operator...')
operator = User.objects.create_user(
    email       = 'operator1@test.com',
    password    = 'testpass2026',
    first_name  = 'Chukwu',
    last_name   = 'Emeka',
    phone       = '08012345678',
    role        = 'op',
    association = association,
)

print('\n' + '='*50)
print('Seed data created successfully.')
print('='*50)
print(f'Association:  {association.name}')
print(f'Super Admin:  admin@iprolance.ng / iproadmin')
print(f'President:    pres@iscooa.ng / pres2026')
print(f'Treasurer:    tres@iscooa.ng / tres2026')
print(f'Secretary:    sec@iscooa.ng / sec2026')
print(f'BOT Chairman: bot.chairman@iscooa.ng / bot2026')
print(f'BOT Member:   bot.member@iscooa.ng / bot2026')
print(f'Adviser:      adv@iscooa.ng / adv2026')
print(f'Operator:     operator1@test.com / testpass2026')
print('='*50)