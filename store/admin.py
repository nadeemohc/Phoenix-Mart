from django.utils.safestring import mark_safe
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import transaction

from .models import (
    Category, SubCategory, Product, ProductVariant,
    Order, CustomUser, OrderItem, Address
)

# --- User Admin ---
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'default_address')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)


# --- Category/SubCategory ---
class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SubCategoryInline]

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("category",)


# --- Variants ---

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    show_change_link = True  # lets you click through to full variant form


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "preview_image")
    list_editable = ("is_active",)
    search_fields = ("name",)
    list_filter = ("category", "is_active")
    ordering = ("name",)
    inlines = [ProductVariantInline]

    def preview_image(self, obj):
        # Show image from the first variant if available
        first_variant = obj.variants.first()
        if first_variant and first_variant.image:
            return mark_safe(f'<img src="{first_variant.image.url}" width="50" height="50" style="object-fit:cover;" />')
        return "—"
    preview_image.short_description = "Image"


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "subcategory", "price", "stock", "in_stock", "is_active", "preview_image")
    list_editable = ("price", "stock", "in_stock", "is_active")
    list_filter = ("subcategory", "in_stock", "is_active")
    search_fields = ("product__name", "subcategory__name")
    ordering = ("product", "subcategory")

    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" style="object-fit:cover;" />')
        return "—"
    preview_image.short_description = "Image"

    def save_model(self, request, obj, form, change):
        # Mark that in_stock is being manually overridden
        obj._manual_in_stock_override = True
        super().save_model(request, obj, form, change)


# --- Orders ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ['product', 'quantity', 'price']
    readonly_fields = ['product', 'quantity', 'price']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'user_phone', 'created_at', 'total_price', 'status', 'COD']
    list_filter = ['status', 'COD', 'created_at']
    list_editable = ('status',)
    search_fields = ['user__email', 'delivery_address']
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {'fields': ('user', 'created_at', 'updated_at', 'status', 'COD')}),
        ('Pricing', {'fields': ('total_price',)}),
        ('Delivery Address', {'fields': ('delivery_address',)}),
    )
    readonly_fields = ['user', 'created_at', 'updated_at', 'total_price', 'COD']

    def user_phone(self, obj):
        return getattr(obj.address, "phone", "—")
    user_phone.short_description = "Phone"

    def save_model(self, request, obj, form, change):
        if change:
            original_obj = Order.objects.get(pk=obj.pk)
            if original_obj.status != 'cancelled' and obj.status == 'cancelled':
                with transaction.atomic():
                    for item in obj.items.all():
                        variant = item.product  # assuming `product` now points to ProductVariant
                        variant.stock += item.quantity
                        variant.save(update_fields=['stock'])
        super().save_model(request, obj, form, change)


# --- Address ---
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "order", "phone", "street", "city", "state", "zipcode", "country")
    list_filter = ("order", "city", "full_name")
