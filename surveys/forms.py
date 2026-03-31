from django import forms

from .services import RATING_LABELS


class QuestionResponseForm(forms.Form):
    response = forms.CharField(required=False)
    other_text = forms.CharField(required=False, max_length=255)

    def __init__(self, area_question, *args, existing_answer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.area_question = area_question
        self.question = area_question.question
        required = area_question.is_required
        question = self.question

        if question.question_type == question.QuestionType.RATING:
            self.fields['response'] = forms.ChoiceField(
                label=question.text,
                required=required,
                choices=[(str(value), label) for value, label in RATING_LABELS.items()],
                widget=forms.RadioSelect,
            )
            if existing_answer and existing_answer.rating_value:
                self.initial['response'] = str(existing_answer.rating_value)

        elif question.question_type == question.QuestionType.YES_NO:
            self.fields['response'] = forms.ChoiceField(
                label=question.text,
                required=required,
                choices=[('yes', 'Sí'), ('no', 'No')],
                widget=forms.RadioSelect,
            )
            if existing_answer and existing_answer.boolean_value is not None:
                self.initial['response'] = 'yes' if existing_answer.boolean_value else 'no'

        elif question.question_type == question.QuestionType.SINGLE_CHOICE:
            self.fields['response'] = forms.ChoiceField(
                label=question.text,
                required=required,
                choices=[(option.value, option.label) for option in question.options.all()],
                widget=forms.RadioSelect,
            )
            if existing_answer and existing_answer.selected_option_id:
                self.initial['response'] = existing_answer.selected_option.value

        elif question.question_type == question.QuestionType.MULTIPLE_CHOICE:
            self.fields['response'] = forms.MultipleChoiceField(
                label=question.text,
                required=required,
                choices=[(option.value, option.label) for option in question.options.all()],
                widget=forms.CheckboxSelectMultiple,
            )
            self.fields['other_text'] = forms.CharField(
                label='Otro: ¿Cuál?',
                required=False,
                max_length=255,
                widget=forms.TextInput(attrs={'placeholder': 'Cuéntanos tu idea'}),
            )
            if existing_answer:
                self.initial['response'] = list(existing_answer.selected_options.values_list('value', flat=True))
                self.initial['other_text'] = existing_answer.text_value

        else:
            self.fields['response'] = forms.CharField(
                label=question.text,
                required=required,
                widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Escribe tu respuesta'}),
            )
            if existing_answer:
                self.initial['response'] = existing_answer.text_value

        self.fields['response'].help_text = question.help_text

    def clean(self):
        cleaned_data = super().clean()
        question = self.question
        response = cleaned_data.get('response')
        other_text = (cleaned_data.get('other_text') or '').strip()

        if question.question_type == question.QuestionType.MULTIPLE_CHOICE:
            selected_values = response or []
            other_option = question.options.filter(is_other_option=True).first()
            if other_option and other_option.value in selected_values and not other_text:
                self.add_error('other_text', 'Debes indicar cuál opción adicional te gustaría encontrar.')

        return cleaned_data

