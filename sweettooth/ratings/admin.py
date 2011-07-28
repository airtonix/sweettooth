
from django.contrib import admin
from django.contrib.comments.admin import CommentsAdmin
from django.utils.translation import ugettext_lazy as _

from ratings.models import RatingComment

class RatingCommentsAdmin(CommentsAdmin):
    fieldsets = (
        (None,
           {'fields': ('content_type', 'object_pk', 'site')}
        ),
        (_('Content'),
           {'fields': ('user', 'user_name', 'user_email', 'rating', 'comment')}
        ),
        (_('Metadata'),
           {'fields': ('submit_date', 'ip_address', 'is_public', 'is_removed')}
        ),
     )

admin.site.register(RatingComment, RatingCommentsAdmin)
