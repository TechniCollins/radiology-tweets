# from django import forms
# from . models import Hashtag


# class hashtagForm(forms.ModelForm):
#     class Meta:
#         model = Hashtag
#         fields = ['name']
#         labels = {'name': 'Hashtag'}

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['category_id'].empty_label = 'Choose a Category'
#         self.fields['category_id'].queryset = Category.objects.filter(is_active=True)
#         self.fields['value_id'].empty_label = 'Choose a Value'
#         self.fields['value_id'].queryset = Tweet.objects.none()
