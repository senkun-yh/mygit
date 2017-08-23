from django import forms
from django.contrib import admin
from django.http import HttpResponse

from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError

# Register your models here.
from .models import *
#from django.utils.html import format_html

## 削除無効化
#admin.site.disable_action('delete_selected')
#def has_delete_permission(self, request, obj=None):
    #return False
#admin.ModelAdmin.has_delete_permission = has_delete_permission

#admin.ModelAdmin.ordering = ('workday',) 

## form.pyに分けて各場合は、下のようにインポートする。
#from .forms import WorkNumberForm,TimeCardForm,TimeCardInlineFormset

class WorkNumberForm(forms.ModelForm):
    class Meta:   # class Meta があってもなくても、変わらない気がする。
        model = WorkNumber
        fields = '__all__'
    def clean(self):
        cleaned_data = self.cleaned_data   
        #cleaned_data['search_key'] = "01162"
        #raise ValidationError('Bla Bla')
        return cleaned_data
    
    
class WorkNumberAdmin(admin.ModelAdmin):    
    form = WorkNumberForm
    list_display = ['work_no', 'work_name','file_link',]
    ordering     = ['work_no',]
    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        form_class.base_fields['work_no'].initial = 'P0000000'
        return form_class

#    def show_work_name(self, obj):
#        return format_html('<a href="http://yahoo.co.jp">yahoo</a>')
    
    '''
    def save_model(self, request, obj, form, change):
        messages.set_level(request, messages.ERROR)
        messages.error(request, '保存できませんでした。')
        return "保存失敗"
    '''
admin.site.register(WorkNumber,WorkNumberAdmin)


class WorkTimeAdmin(admin.ModelAdmin):
    #form = WorkNumberForm
    #exclude = ['create_user',]
    list_display = ['time_card', 'work_number','work_hour','auth_flg',]
    ordering     = ['time_card','work_number',]
    # class Meta:
    #    fields='__all__'
    def get_queryset(self, request):
        qs = super(WorkTimeAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        # 自分のIDでフィルターかける
        return qs.filter(work_number__work_reps__contains=request.user)
    
    ## Action
    actions = ['batch_update_auth']
    
    def batch_update_auth(modeladmin, request, queryset):
        for q in queryset:
            q.auth_flg = True
            q.save()
        messages.success(request,'一括承認が完了しました。')   
        #queryset.delete()
    batch_update_auth.short_description = "一括承認"
    
admin.site.register(WorkTime,WorkTimeAdmin)

class TimeCardInlineFormset(forms.models.BaseInlineFormSet):    
    def clean_work_name(self):
        cleaned_data = self.cleaned_data
        return cleaned_data
    
    def clean(self):
        cleaned_data = self.cleaned_data  
        #if self.is_valid:
        rt = 0
        try:
            for v in cleaned_data:
                rt = rt + v.get('work_hour',0)
            if rt != cleaned_data[0]['time_card'].work_sum:
                raise forms.ValidationError("合計時間と明細時間の合計が一致していません。") 
        except:
            raise forms.ValidationError("入力に誤りがあります。正しく入力してください。")
        return cleaned_data

# Inline モデルを定義
# class WorkTimeInline(admin.StackedInline):
class WorkTimeInline(admin.TabularInline):
    exclude      = ['auth_flg',]
    model = WorkTime
    extra = 5
    formset = TimeCardInlineFormset
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "work_number":
            qs = WorkNumber.objects.all()
            if request.user.is_superuser:
                kwargs["queryset"] = qs
            if request.user.is_superuser == False:
                #kwargs["queryset"] = qsn.filter(search_key=request.user)        
                kwargs["queryset"] = qs.filter(work_stfs__contains=request.user)        
        return super(WorkTimeInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class TimeCardForm(forms.ModelForm):
    class Meta:
        model = TimeCard
        fields = ['work_day','work_sum','work_user']

    def clean(self):
        cleaned_data = self.cleaned_data
        #raise ValidationError(cleaned_data['work_sum'])
        return cleaned_data

class TimeCardAdmin(admin.ModelAdmin):
    form = TimeCardForm
    list_display  = ['work_day', "work_user",]
    exclude       = ['create_user',]
    ordering      = ['work_day','work_sum']
    #raw_id_fields = ("work_user",)
    #radio_fields = {"work_user": admin.VERTICAL}
    #search_fields = ['work_day',]   
    #search_fields = ['worktime__work_number']   #[foreign_key__related_fieldname]
#    fieldsets = [
#        (None,               {'fields': ['work_number']}),
#        ('Date information', {'fields': ['work_hour']}),
#    ]
    inlines = [WorkTimeInline]
    # 初期値設定
    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        form_class.base_fields['work_user'].initial = request.user
        return form_class

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "work_user":
            kwargs["queryset"] = User.objects.filter(username=request.user)
            qs = User.objects.all()
            if request.user.is_superuser:
                kwargs["queryset"] = qs
            if request.user.is_superuser == False:
                kwargs["queryset"] = qs.filter(username=request.user)        
        return super(TimeCardAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super(TimeCardAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        # 自分のIDでフィルターかける
        return qs.filter(work_user=request.user)

    def save_model(self, request, obj, form, change):
        #if change is False:
        obj.create_user = request.user
        obj.save()

admin.site.register(TimeCard,TimeCardAdmin)

