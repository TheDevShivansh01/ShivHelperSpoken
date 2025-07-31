from telegram import Update, PollAnswer, Poll, InlineKeyboardButton, InlineKeyboardMarkup

DIFFICULTY_MAP = {
    # Grammar
    'difficulty_synonyms': ('Data/SYNO5.xlsx', 'Synonyms'),
    'difficulty_prepo': ('Data/English_Preposition.xlsx', 'Preposition'),
    'difficulty_antonyms': ('Data/Antonyms5.xlsx', 'Antonyms'),
    'difficulty_spellcorr': ('Data/spellCorrection4old.xlsx', 'Spelling Correction'),
    'difficulty_sentcorr': ('Data/sentenceCorr4.xlsx', 'Sentence Correction'),
    'difficulty_shortIdiom': ('Data/basic_shortidiom.xlsx', 'Daily Life Idioms'),

    # NEET
    'difficulty_neetchemistry': ('Data/Neet_Chemistry.xlsx', 'Chemistry'),

    # Topics
    'difficulty_vedicSociety': ('Data/VedicSociety.xlsx', 'Vedic Society'),
     'difficulty_worldtop': ('Data/WorldTop.xlsx', 'World First'),
    'difficulty_sangamPeriod': ('Data/SangamPeriod.xlsx', 'Sangam Period'),
    'difficulty_PreMaurya': ('Data/PreMauryaPeriod.xlsx', 'Pre Maurya Period'),
    'difficulty_bloodrelation': ('Data/BloodRelation.xlsx', 'Blood Relation'),
    'difficulty_bookwriter': ('Data/BookWriter.xlsx', 'Book and Writer'),
    'difficulty_IndiaGs': ('Data/India_GS.xlsx', 'About India'),
    'difficulty_indianPolity': ('Data/IndianPolity.xlsx', 'Indian Polity'),
    'difficulty_indusvalley': ('Data/Indus_Valley.xlsx', 'Indus Valley Civilisation'),
    'difficulty_IndiaConstitute': ('Data/IndianConstitution.xlsx', 'Indian Constitution'),
    'difficulty_artandculture': ('Data/ArtandCulture.xlsx', 'Art and Culture'),
    'difficulty_BgngOfModernAge': ('Data/BeginingOfModernAge.xlsx', 'Begining of Modern Age'),
    'difficulty_Mauryaempire': ('Data/mauryaEmpire.xlsx', 'Maurya Empire'),

    # NDA
    'difficulty_synonyms_nda': ('Data/Nda_Synonyms_updated.xlsx', 'Synonyms'),
    'difficulty_acitvepassive_nda': ('Data/NDA_active_passive_voice1.xlsx', 'Active passive Voice'),
    'difficulty_fillblank_nda': ('Data/Nda_FillinTheBlanks.xlsx', 'Fill in the blanks'),
    'difficulty_idiomphrase_nda': ('Data/Nda_Idiom.xlsx', 'Idiom Phrase'),
    'difficulty_nda_ows': ('Data/Nda_OneWord.xlsx', 'One word Substitution'),
    'difficulty_nda_antonyms': ('Data/Nda_Antonyms.xlsx', 'Antonyms'),

    # UPSC
    'difficulty_upscpreviousyear': ('Data/UPSC_GS_2023.xlsx', 'GS-Previous years paper'),
    'difficulty_upschistory': ('Data/Upsc_history.xlsx', 'History'),
    'difficulty_upscscience': ('Data/Upsc_ScienceandTech.xlsx', 'Science and Technology'),
    'difficulty_thehindu': ('Data/thehindu.xlsx', 'Science and Technology'),

    'difficulty_upscpresident': ('Data/IP_ThePresident.xlsx', 'The President'),
    'difficulty_upscunionandstatefunction': ('Data/IP_FnResp_ofTheUnionandStates.xlsx', ' Union and State Function and Responsibilities'),
    'difficulty_upscseperationofpower': ('Data/IP_SeperationofPower.xlsx', 'Separation of Power'),
    'difficulty_upscstruggleforswaraj': ('Data/MH_StruggleofSwaraj.xlsx', 'Modern history - Struggle for Swaraj'),
    'difficulty_upscearlynationalism': ('Data/MH_EarlyNationalism.xlsx', 'Modern history - Early Nationalism'),
    'difficulty_upscrevolt1857': ('Data/MH_TheRevolt.xlsx', 'Modern history - Revolt of 1857'),
    'difficulty_upscDPSP': ('Data/IP_DPSP.xlsx', 'Indion Polity - DPSP'),
    'difficulty_judiciarysystem': ('Data/IPJudicialSystem.xlsx', 'Judiciary System'),
    'difficulty_parliament': ('Data/IPParliament.xlsx', 'Parliament'), 
    'difficulty_primeminister': ('Data/IPPrimeminister.xlsx', 'Prime Minister'),

    # History

    'difficulty_historyAncient': ('Data/AncientHistory.xlsx', 'Ancient History'),
    'difficulty_historyMedieval': ('Data/MedivalHistory.xlsx', 'Medieval History'),
    'difficulty_historyModern': ('Data/ModernHistory.xlsx', 'Modern History'),

    # CGL
    'difficulty_cglGk': ('Data/CGL_GK.xlsx', 'General Awareness'),
    'difficulty_cglEnglish': ('Data/CGL_English.xlsx', 'Englsih'),
    'difficulty_cglReasoning': ('Data/CGL_Reasoning.xlsx', 'Reasoning'),

        #Reasoning
    'difficulty_syllogism': ('Data/Sylogism.xlsx', 'Syllogism'),
     'difficulty_NumberAlphabetSeries': ('Data/numberalphabet.xlsx', 'Number and Alphabet Series'),
      'difficulty_OddOneOut': ('Data/OddOneOut.xlsx', 'Odd One Out'),
}

def Reasoning_Kb0():
    return [
          [InlineKeyboardButton("Odd One Out", callback_data='difficulty_OddOneOut')],
           [InlineKeyboardButton("Number Alphabet Series", callback_data='difficulty_NumberAlphabetSeries')],
           [InlineKeyboardButton("Sylogism", callback_data='difficulty_syllogism')],
           [InlineKeyboardButton("Reasoning", callback_data='difficulty_cglReasoning')]
        
    ]

def StartingSubject0():
    return [
        [InlineKeyboardButton("English Grammar", callback_data='type_BASIC')],
        [InlineKeyboardButton("Reasoning", callback_data='type_reasoning')],
        [InlineKeyboardButton("History Interesting Topic", callback_data='type_topic0')],
        [InlineKeyboardButton("UPSC", callback_data='type_Upsc0')],
        [InlineKeyboardButton("SSC - CGL/CHSL", callback_data='type_Cgl')],
        [InlineKeyboardButton("🧑‍🦯‍➡️ Next 🧑‍🦯‍➡️", callback_data='type_startsubj1')]
    ]   
def StartingSubject1():
    return [
     [InlineKeyboardButton("NDA-CDS", callback_data='type_NDA0')],
    [InlineKeyboardButton("History", callback_data='type_History')],
     [InlineKeyboardButton("Jee and Neet", callback_data='type_Neet')],
     [InlineKeyboardButton("🏎️  Previous", callback_data='type_startsubj0')]
    ]   
def Nda_keyboard0():
    return [
        [InlineKeyboardButton("Synonyms", callback_data='difficulty_synonyms_nda')],
        [InlineKeyboardButton("Antonyms", callback_data='difficulty_nda_antonyms')],
        [InlineKeyboardButton("Idiom-Phrase", callback_data='difficulty_idiomphrase_nda')],
        [InlineKeyboardButton("One word Substitute", callback_data='difficulty_nda_ows')],
        [InlineKeyboardButton("🧑‍🦯‍➡️ Next 🧑‍🦯‍➡️", callback_data='type_NDA1')]
    ]        

def Nda_keyboard1():
    return [
        
        [InlineKeyboardButton("Active-passive", callback_data='difficulty_acitvepassive_nda')],
        [InlineKeyboardButton("🏎️  Previous ", callback_data='type_NDA0'),InlineKeyboardButton("Next 🧑‍🦯‍➡️", callback_data='type_NDA2')],
        
    ]
def Nda_keyboard2():
    return [
       [InlineKeyboardButton("Fill in the Blanks", callback_data='difficulty_fillblank_nda')],
        [InlineKeyboardButton("🏎️  Previous", callback_data='type_NDA1'),InlineKeyboardButton("Next 🧑‍🦯‍➡️", callback_data='type_NDA0')]
        
    ]
def Topic_Kb0():
    return [
        [InlineKeyboardButton("Blood Relation", callback_data='difficulty_bloodrelation')],
        [InlineKeyboardButton("World First", callback_data='difficulty_worldtop')],
        [InlineKeyboardButton("Book - Writer", callback_data='difficulty_bookwriter')],
        [InlineKeyboardButton("Indian Polity", callback_data='difficulty_indianPolity')],
        [InlineKeyboardButton("Indus Valley Civilization", callback_data='difficulty_indusvalley')],
      
        [InlineKeyboardButton("🧑‍🦯‍➡️ Next 🧑‍🦯‍➡️", callback_data='type_topic1')]
    ]        

def Topic_Kb1():
    return [
          [InlineKeyboardButton("Indian Constitution", callback_data='difficulty_IndiaConstitute')],
           [InlineKeyboardButton("About India", callback_data='difficulty_IndiaGs')],
           [InlineKeyboardButton("Art & Culture", callback_data='difficulty_artandculture')],
           [InlineKeyboardButton("Begining of Modern Age", callback_data='difficulty_BgngOfModernAge')],
        [InlineKeyboardButton("🏎️  Previous ", callback_data='type_topic0'),InlineKeyboardButton("Next 🧑‍🦯‍➡️", callback_data='type_topic2')],
        
    ]

def Upsc_keyboard0():
    return [
        [InlineKeyboardButton("IP-The President", callback_data='difficulty_upscpresident')],
         [InlineKeyboardButton("GS-Previous Year Paper", callback_data='difficulty_upscpreviousyear')],
                [InlineKeyboardButton("The Hindu Vocab", callback_data='difficulty_thehindu')],
                [InlineKeyboardButton("History", callback_data='difficulty_upschistory')],
                [InlineKeyboardButton("Science Tech", callback_data='difficulty_upscscience')],
                [InlineKeyboardButton("Revolt of 1857", callback_data='difficulty_upscrevolt1857')],
                
        [InlineKeyboardButton("Next 🧑‍🦯‍➡️", callback_data='type_Upsc1')],
    ]  

def Upsc_keyboard1():
    return [
         [InlineKeyboardButton("Early Nationalism", callback_data='difficulty_upscearlynationalism')],
                [InlineKeyboardButton("Struggle for swaraj", callback_data='difficulty_upscstruggleforswaraj')],
                [InlineKeyboardButton("IP-DPSP", callback_data='difficulty_upscDPSP')],
                [InlineKeyboardButton("IP-Seperation of Power", callback_data='difficulty_upscseperationofpower')],
                [InlineKeyboardButton("Union and State Function and Resp", callback_data='difficulty_upscunionandstatefunction')],
                
        [InlineKeyboardButton("🏎️  Previous ", callback_data='type_Upsc0'),InlineKeyboardButton("Next 🧑‍🦯‍➡️", callback_data='type_Upsc2')],
    ]  
def Upsc_keyboard2():
    return [
         [InlineKeyboardButton("IP- Parliament", callback_data='difficulty_parliament')],
                [InlineKeyboardButton("IP -Primeminister", callback_data='difficulty_primeminister')],
                [InlineKeyboardButton("IP-Judiciary System", callback_data='difficulty_judiciarysystem')],
               
        [InlineKeyboardButton("🏎️  Previous ", callback_data='type_Upsc1'),InlineKeyboardButton("Next 🧑‍🦯‍➡️", callback_data='type_Upsc0')],
    ] 
def Topic_Kb2():
    return [
          [InlineKeyboardButton("Maurya Empire", callback_data='difficulty_Mauryaempire')],
           [InlineKeyboardButton("Pre Maurya Period", callback_data='difficulty_PreMaurya')],
           [InlineKeyboardButton("Sangam Period", callback_data='difficulty_sangamPeriod')],
           [InlineKeyboardButton("Vedic Society", callback_data='difficulty_vedicSociety')],
        [InlineKeyboardButton("🏎️  Previous", callback_data='type_topic1'),InlineKeyboardButton("Next 🧑‍🦯‍➡️", callback_data='type_topic0')]
        
    ]



ALLOWED_FILES = {
    "SYNO5",
    "IPJudicialSystem",
    "IPParliament",
    "IPPrimeminister",
    "Antonyms5",
    "spellCorrection4",
    "basic_shortidiom",
    "Nda_FillinTheBlanks",
    "Nda_Idiom",
    "English_Preposition",
    "Nda_OneWord",
    "thehindu",
    "CGL_English",
    "CGL_GK",
    "AncientHistory",
    "MedivalHistory",
    "ModernHistory",
    "BloodRelation",
    "BookWriter",
    "CGL_Reasoning",
    "India_GS",
    "IndianPolity",
    "Indus_Valley",
    "ArtandCulture",
    "BeginingOfModernAge",
    "IndianConstitution",
    "mauryaEmpire",
    "PreMauryaPeriod",
    "SangamPeriod",
    "VedicSociety",
    "NDA_active_passive_voice1",
    "WorldTop",
    "Cgl_Quant",
    "indus",
    "spellCorrection4old",
    "Nda_Synonyms_updated",
    "Neet_Chemistry",
    "UPSC_GS_2023",
    "Upsc_history",
    "Upsc_ScienceandTech",
    "IP_DPSP",
    "IP_FnResp_ofTheUnionandStates",
    "IP_SeperationofPower",
    "MH_StruggleofSwaraj",
    "MH_EarlyNationalism",
    "MH_TheRevolt",
    "IP_ThePresident",
    "OddOneOut",
    "numberalphabet",
    "Sylogism",
}