from googletrans import Translator ,LANGUAGES

class TranslationService:
    def __init__(self):
        self.translator = Translator()
        self.languages ={
            'en': 'English',
            'hi': 'Hindi'

        }

        def get_supported_languages(self):
            return self.languages
        
        def translate(self, text, target_lang):
            if target_lang=='en' or not text:
                return text
            try:
                translated = self.translator.translate(text, dest=target_lang)
                return translated.text
            except Exception as e:
               print(f"Translation error: {e}")
            return text
        
        def translate_dict(self, content_dict, target_lang):
            return {key: self.translate_text(value, target_lang) for key, value in content_dict.items()}
