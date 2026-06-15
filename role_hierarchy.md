
##### The Hierarchy - Who Has More Power? #####

                    SA (Super Admin - Iprolance)
                    │ (Owns the software, can see everything)
                    │
                    BOT (Board of Trustees)
                    │ (Oversees ISCOOA, approves big decisions)
                    │
                    IS (ISCOOA Executives)
                    │ (Run day-to-day operations)
                    │
        ┌───────────┼───────────┐
        │           │           │
    Treasurer   Secretary   President
        │           │           │
        └───────────┴───────────┘
                    │
                    ADV (Legal Adviser)
                    │ (Independent, advises all levels)
                    │
                    OP (Operators)
                    (Normal shop owners)







##### The Code and Full Meaning #####
Code	Full Meaning(IPOS)	Who Has It
'op'	Operator	        Shop owners
'is'	ISCOOA	            ISCOOA executives (Treasurer, Secretary, President) 
'adv'	Adviser	            Legal Adviser
'bot'	Bot	            Automated system accounts. Board of Trustees, It's a group of importantPeople
'sa'	Super Admin	    Iprolance (YOU) - the platform owner




##### What 'sa' Can Do That Others Cannot ######
Feature                 	op	     is	      adv	sa
View own shop/bills	        ✅	    ❌	    ❌	✅
View ALL shops/bills	    ❌	    ✅	    ❌	✅
View audit log	            ❌	    ❌	    ❌	✅
View ALL wallets	        ❌	    ✅	    ❌	✅
Access Django admin	        ❌	    ❌	    ❌	✅
Change system settings  	❌	    ❌	    ❌	✅
See revenue reports	        ❌	    ✅	    ❌	✅




###### Why 'sa' Exists ########
'sa' = The Owner of the Platform

In your case:

ISCOOA runs the market

Iprolance (YOU) built the software

Iprolance needs oversight to make sure ISCOOA is not cheating

Think of it like:

ISCOOA = Mall management

Iprolance = Company that built the mall's security system

Iprolance can monitor everything to ensure mall management is honest










###### What is the Expenses Module? ######
Expenses Module = How ISCOOA spends money that needs approval.
Why It's Complex
Because different amounts need different levels of approval:

    The Approval Flow Diagram 👇🏽
Employee wants to buy something
           ↓
     Submits expense request
           ↓
    ┌──────┴──────┐
    ↓             ↓
Below ₦500k    Above ₦500k
    ↓             ↓
Treasurer    Treasurer approves
    ↓             ↓
   DONE      Secretary General
                   ↓
              ┌────┴────┐
              ↓         ↓
         Below ₦5M   Above ₦5M
              ↓         ↓
            DONE     President
                        ↓
                     BOT ratifies
                        ↓
                      DONE









pls make me understand this ISCOOA , i understand u said ISCOOA  is the company that but the app that is using it for complex or extate then Iprolance is we the app owner.

Hold On First Before We Move On To Supabase Migration
i rember the md said we should make it whitelable if i understand it means where other company can buy and use the app then edith it to their tast like the logo and color am i correct, now how can i make the app whitelable, again if u see my business logic u can see i already use is ISCOOA  to write most logic it means the system is only specifically design for the ISCOOA , what can i do exactly, and what are the step for me to convert to whitelable.

can i still go ahead and send the schema json file to the frontend dev and start building, hope if i build the frontend now it will it affect anything or will require touhing later when am ready to convert or is just my backend that will require the touch. what do you advise for us to do first, whether i should go ahead send the doc to frontend to continue building or i should update the entire app to work with whitelabel ones and for all, You as my senior engr just tell me which one we should do. 






TODAY
└── Send schema.json to frontend engineer — they start building

NEXT (Backend — parallel to frontend)
├── Step 27: White-Label Implementation
│   ├── Phase A: Association and Config models
│   ├── Phase B: Link existing data to associations
│   ├── Phase C: Dynamic business rules
│   ├── Phase D: Dynamic text and branding
│   └── Phase E: Config API endpoint for frontend
│
├── Step 28: Supabase Migration
└── Step 29: Deployment

LATER (Small frontend update)
└── Frontend reads association config from API
    instead of hardcoded ISCOOA values
    (1-2 hours of work for the frontend engineer)