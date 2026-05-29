from django.contrib import admin

from .models import Brokerage


@admin.register(Brokerage)
class BrokerageAdmin(admin.ModelAdmin):
    list_display = ('trade_name', 'legal_name', 'cnpj', 'plan', 'is_active')
    list_filter = ('is_active', 'plan')
    search_fields = ('legal_name', 'trade_name', 'cnpj')
    ordering = ('trade_name',)