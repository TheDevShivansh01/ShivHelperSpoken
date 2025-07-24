from telegram import Update, PollAnswer, Poll, InlineKeyboardButton, InlineKeyboardMarkup

DIFFICULTY_MAP = {
    # Grammar
    'difficulty_synonyms': ('Data/SYNO5.xlsx', 'Synonyms'),
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

    # History
    'difficulty_historyAncient': ('Data/AncientHistory.xlsx', 'Ancient History'),
    'difficulty_historyMedieval': ('Data/MedivalHistory.xlsx', 'Medieval History'),
    'difficulty_historyModern': ('Data/ModernHistory.xlsx', 'Modern History'),

    # CGL
    'difficulty_cglGk': ('Data/CGL_GK.xlsx', 'General Awareness'),
    'difficulty_cglEnglish': ('Data/CGL_English.xlsx', 'Englsih'),
    'difficulty_cglReasoning': ('Data/CGL_Reasoning.xlsx', 'Reasoning'),
}

def StartingSubject0():
    return [
        [InlineKeyboardButton("English Grammar", callback_data='type_BASIC')],
        [InlineKeyboardButton("History Interesting Topic", callback_data='type_topic0')],
        [InlineKeyboardButton("UPSC", callback_data='type_Upsc')],
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
    "Antonyms5",
    "spellCorrection4",
    "basic_shortidiom",
    "Nda_FillinTheBlanks",
    "Nda_Idiom",
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
    "Upsc_ScienceandTech"
}