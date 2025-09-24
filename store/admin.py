from django.utils.safestring import mark_safe
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from .models import Category, SubCategory, Product, Order, CustomUser, OrderItem, Address

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

# Inline for SubCategory inside Category
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


class OrderItemInline(admin.TabularInline):
    """
    Defines the inline representation of OrderItem for the Django admin.
    This allows OrderItem objects to be edited directly on the Order page.
    """
    model = OrderItem
    extra = 0
    fields = ['product', 'quantity', 'price']
    readonly_fields = ['product', 'quantity', 'price']


# Use a decorator to register the Order model with the custom admin class
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Customizes the Django admin interface for the Order model.
    """
    # 'list_display' controls which fields are shown on the change list page.
    list_display = ['id', 'user', 'user_phone', 'created_at', 'total_price', 'status', 'COD']
    
    # 'list_filter' adds a sidebar for filtering the list.
    list_filter = ['status', 'COD', 'created_at']

    list_editable = ('status',)
    
    # 'search_fields' enables a search box for these fields.
    search_fields = ['user__email', 'delivery_address']
    
    # 'inlines' is the key part that includes the OrderItemInline.
    # This displays the related OrderItems on the Order's detail page.
    inlines = [OrderItemInline]

    # 'fieldsets' can be used to group fields in the detail view.
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'created_at', 'updated_at', 'status', 'COD'),
        }),
        ('Pricing', {
            'fields': ('total_price',),
        }),
        ('Delivery Address', {
            'fields': ('delivery_address',),
        }),
    )

    # 'readonly_fields' prevents these fields from being edited.
    readonly_fields = ['user', 'created_at', 'updated_at', 'total_price', 'COD']
    
    # Custom column to show user phone
    def user_phone(self, obj):
        return obj.address.phone or "—"
    user_phone.short_description = "Phone"

    def save_model(self, request, obj, form, change):
        """
        Overrides the save behavior to manage stock when an order is cancelled.
        """
        # Get the original object from the database before the form changes are saved
        if change:
            original_obj = Order.objects.get(pk=obj.pk)

            # Check if the status has been changed to 'cancelled'
            if original_obj.status != 'cancelled' and obj.status == 'cancelled':
                with transaction.atomic():
                    # Return items to stock
                    for item in obj.items.all():
                        product = item.product
                        product.stock += item.quantity
                        product.save(update_fields=['stock'])
                        
        # Save the Order object after handling the stock
        super().save_model(request, obj, form, change)
# Register the Product model as well for completeness
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "subcategory", "price", "stock", "in_stock", "preview_image")
    list_editable = ("price", "stock", "in_stock")
    list_filter = ("category", "subcategory")
    search_fields = ("name",)
    ordering = ("name",)

    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" style="object-fit:cover;" />')
        return "No Image"
    
    preview_image.short_description = "Image"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "order", "phone", "street", "city", "state", "zipcode", "country")
    list_filter = ("order", "city", "full_name")
    # search_fields = ("")