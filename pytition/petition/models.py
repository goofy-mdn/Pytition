from django.db import models
from django.utils.html import mark_safe, strip_tags
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

from tinymce import models as tinymce_models
from colorfield.fields import ColorField

import html


class Petition(models.Model):

    NO =           "no gradient"
    RIGHT =        "to right"
    BOTTOM =       "to bottom"
    BOTTOM_RIGHT = "to bottom right"
    BOTTOM_LEFT =  "to bottom left"

    LINEAR_GRADIENT_CHOICES = (
        (NO,           "no gradient"),
        (RIGHT,        "to right"),
        (BOTTOM,       "to bottom"),
        (BOTTOM_RIGHT, "to bottom right"),
        (BOTTOM_LEFT,  "to bottom left")
    )

    MAIL = "MAIL"
    POST = "POST"
    GET = "GET"

    NEWSLETTER_SUBSCRIBE_METHOD_CHOICES = (
        (MAIL, "MAIL"),
        (POST, "POST"),
        (GET,  "GET")
    )

    title = models.TextField(verbose_name=ugettext_lazy("Title"))
    text = tinymce_models.HTMLField(blank=True)
    side_text = tinymce_models.HTMLField(blank=True)
    target = models.IntegerField(default=500)
    linear_gradient_direction = models.CharField(choices=LINEAR_GRADIENT_CHOICES, max_length=15, default=NO, blank=True)
    gradient_from = ColorField(blank=True)
    gradient_to = ColorField(blank=True)
    bgcolor = ColorField(blank=True)
    footer_text = tinymce_models.HTMLField(blank=True)
    footer_links = tinymce_models.HTMLField(blank=True)
    twitter_description = models.CharField(max_length=200, blank=True)
    twitter_image = models.CharField(max_length=500, blank=True)
    has_newsletter = models.BooleanField(default=False)
    newsletter_subscribe_http_data = models.TextField(blank=True)
    newsletter_subscribe_http_mailfield = models.CharField(max_length=100, blank=True)
    newsletter_subscribe_http_url = models.CharField(max_length=1000, blank=True)
    newsletter_subscribe_mail_subject = models.CharField(max_length=1000, blank=True)
    newsletter_subscribe_mail_from = models.CharField(max_length=500, blank=True)
    newsletter_subscribe_mail_to = models.CharField(max_length=500, blank=True)
    newsletter_subscribe_method = models.CharField(choices=NEWSLETTER_SUBSCRIBE_METHOD_CHOICES, max_length=4,
                                                   default=MAIL)
    newsletter_subscribe_mail_smtp_host = models.CharField(max_length=100, default='localhost', blank=True)
    newsletter_subscribe_mail_smtp_port = models.IntegerField(default=25, blank=True)
    newsletter_subscribe_mail_smtp_user = models.CharField(max_length=200, blank=True)
    newsletter_subscribe_mail_smtp_password = models.CharField(max_length=200, blank=True)
    newsletter_subscribe_mail_smtp_tls = models.BooleanField(default=False)
    newsletter_subscribe_mail_smtp_starttls = models.BooleanField(default=False)
    org_twitter_handle = models.CharField(max_length=20, blank=True)
    published = models.BooleanField(default=False)
    newsletter_text = models.CharField(max_length=1000, blank=True)
    sign_form_footer = models.TextField(blank=True)
    confirmation_email_sender = models.CharField(max_length=100, blank=True)
    confirmation_email_smtp_host = models.CharField(max_length=100, default='localhost', blank=True)
    confirmation_email_smtp_port = models.IntegerField(default=25, blank=True)
    confirmation_email_smtp_user = models.CharField(max_length=200, blank=True)
    confirmation_email_smtp_password = models.CharField(max_length=200, blank=True)
    confirmation_email_smtp_tls = models.BooleanField(default=False)
    confirmation_email_smtp_starttls = models.BooleanField(default=False)
    use_custom_email_settings = models.BooleanField(default=False)

    @classmethod
    def by_id(cls, id):
        try:
            return Petition.objects.get(pk=id)
        except Petition.DoesNotExist:
            return None

    def get_signature_number(self, confirmed=None):
        signatures = self.signature_set
        if confirmed is not None:
            signatures = signatures.filter(confirmed=confirmed)
        return signatures.count()

    def already_signed(self, email):
        signature_number = Signature.objects.filter(petition = self.id)\
            .filter(confirmed = True).filter(email = email).count()
        return signature_number > 0

    def confirm_signature(self, conf_hash):
        signature = Signature.objects.filter(petition=self.id).get(confirmation_hash=conf_hash)
        if signature:
            # Now confirm the signature corresponding to this hash
            signature.confirm()
            signature.save()
            return _("Thank you for confirming your signature!")
        else:
            return None

    def publish(self):
        self.published = True
        self.save()

    def unpublish(self):
        self.published = False
        self.save()

    @property
    def signature_number(self):
        return self.get_signature_number(True)

    @property
    def raw_twitter_description(self):
        return html.unescape(mark_safe(strip_tags(self.twitter_description)))

    @property
    def raw_text(self):
        return html.unescape(mark_safe(strip_tags(self.text)))

    @property
    def raw_title(self):
        return html.unescape(mark_safe(strip_tags(self.title).strip()))

    def __str__(self):
        return self.raw_title

    def __repr__(self):
        return self.raw_title


class Signature(models.Model):
    first_name = models.CharField(max_length=50, verbose_name=ugettext_lazy("First name"))
    last_name = models.CharField(max_length=50, verbose_name=ugettext_lazy("Last name"))
    phone = models.CharField(max_length=20, blank=True, verbose_name=ugettext_lazy("Phone number"))
    email = models.EmailField(verbose_name=ugettext_lazy("Email address"))
    confirmation_hash = models.CharField(max_length=128)
    confirmed = models.BooleanField(default=False, verbose_name=ugettext_lazy("Confirmed"))
    petition = models.ForeignKey(Petition, on_delete=models.CASCADE, verbose_name=ugettext_lazy("Petition"))
    subscribed_to_mailinglist = models.BooleanField(default=False, verbose_name=ugettext_lazy("Subscribed to mailing list"))
    date = models.DateTimeField(blank=True, auto_now_add=True, verbose_name=ugettext_lazy("Date"))

    def clean(self):
        if self.petition.already_signed(self.email):
            if self.petition.signature_set.filter(email = self.email).get(confirmed = True).id != self.id:
                raise ValidationError(_("You already signed the petition"))

    def save(self, *args, **kwargs):
        self.clean()
        if self.confirmed:
            # invalidating other signatures from same email
            Signature.objects.filter(petition=self.petition).filter(email=self.email)\
                .exclude(id=self.id).delete()
        super().save(*args, **kwargs)

    def confirm(self):
        self.confirmed = True

    def __str__(self):
        return html.unescape("[{}:{}] {} {}".format(self.petition.id, "OK" if self.confirmed else "..", self.first_name,
                                                    self.last_name))

    def __repr__(self):
        return html.unescape("[{}:{}] {} {}".format(self.petition.id, "OK" if self.confirmed else "..", self.first_name,
                                                    self.last_name))


class PetitionTemplate(models.Model):

    NO =           "no gradient"
    RIGHT =        "to right"
    BOTTOM =       "to bottom"
    BOTTOM_RIGHT = "to bottom right"
    BOTTOM_LEFT =  "to bottom left"

    LINEAR_GRADIENT_CHOICES = (
        (NO,           "no gradient"),
        (RIGHT,        "to right"),
        (BOTTOM,       "to bottom"),
        (BOTTOM_RIGHT, "to bottom right"),
        (BOTTOM_LEFT,  "to bottom left")
    )

    MAIL = "MAIL"
    POST = "POST"
    GET = "GET"

    NEWSLETTER_SUBSCRIBE_METHOD_CHOICES = (
        (MAIL, "MAIL"),
        (POST, "POST"),
        (GET,  "GET")
    )

    name = models.CharField(max_length=50, verbose_name=ugettext_lazy("Name"), db_index=True)
    text = tinymce_models.HTMLField(blank=True)
    side_text = tinymce_models.HTMLField(blank=True)
    target = models.IntegerField(blank=True, null=True)
    linear_gradient_direction = models.CharField(choices=LINEAR_GRADIENT_CHOICES, max_length=15, default=NO, blank=True)
    gradient_from = ColorField(blank=True)
    gradient_to = ColorField(blank=True)
    bgcolor = ColorField(blank=True)
    footer_text = tinymce_models.HTMLField(blank=True)
    footer_links = tinymce_models.HTMLField(blank=True)
    twitter_description = models.CharField(max_length=200, blank=True)
    twitter_image = models.CharField(max_length=500, blank=True)
    has_newsletter = models.BooleanField(default=False)
    newsletter_subscribe_http_data = models.TextField(blank=True)
    newsletter_subscribe_http_mailfield = models.CharField(max_length=100, blank=True)
    newsletter_subscribe_http_url = models.CharField(max_length=1000, blank=True)
    newsletter_subscribe_mail_subject = models.CharField(max_length=1000, blank=True)
    newsletter_subscribe_mail_from = models.EmailField(max_length=500, blank=True)
    newsletter_subscribe_mail_to = models.EmailField(max_length=500, blank=True)
    newsletter_subscribe_method = models.CharField(choices=NEWSLETTER_SUBSCRIBE_METHOD_CHOICES, max_length=4,
                                                   default=MAIL)
    newsletter_subscribe_mail_smtp_host = models.CharField(max_length=100, default='localhost', blank=True)
    newsletter_subscribe_mail_smtp_port = models.IntegerField(default=25)
    newsletter_subscribe_mail_smtp_user = models.CharField(max_length=200, blank=True)
    newsletter_subscribe_mail_smtp_password = models.CharField(max_length=200, blank=True)
    newsletter_subscribe_mail_smtp_tls = models.BooleanField(default=False)
    newsletter_subscribe_mail_smtp_starttls = models.BooleanField(default=False)
    org_twitter_handle = models.CharField(max_length=20, blank=True)
    newsletter_text = models.CharField(max_length=1000, blank=True)
    sign_form_footer = models.TextField(blank=True)
    confirmation_email_sender = models.EmailField(max_length=100, blank=True)
    confirmation_email_smtp_host = models.CharField(max_length=100, default='localhost', blank=True)
    confirmation_email_smtp_port = models.IntegerField(default=25, blank=True)
    confirmation_email_smtp_user = models.CharField(max_length=200, blank=True)
    confirmation_email_smtp_password = models.CharField(max_length=200, blank=True)
    confirmation_email_smtp_tls = models.BooleanField(default=False)
    confirmation_email_smtp_starttls = models.BooleanField(default=False)
    use_custom_email_settings = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    class Meta:
        index_together = ["id", ]


class Organization(models.Model):
    name = models.CharField(max_length=200, verbose_name=ugettext_lazy("Name"))
    petition_templates = models.ManyToManyField(PetitionTemplate, through='TemplateOwnership',
                                                through_fields=['organization', 'template'], blank=True,
                                                verbose_name=ugettext_lazy("Petition templates"))
    petitions = models.ManyToManyField(Petition, blank=True, verbose_name=ugettext_lazy("Petitions"))
    default_template = models.ForeignKey(PetitionTemplate, blank=True, null=True, related_name='+',
                                         verbose_name=ugettext_lazy("Default petition template"), to_field='id',
                                         on_delete=models.SET_NULL)

    def add_member(self, member):
        member.organizations.add(self)
        permission = Permission.objects.create(organization=self)
        permission.save()
        member.permissions.add(permission)
        member.save()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    @property
    def kind(self):
        return "org"

    @property
    def fullname(self):
        return self.name

class Permission(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name=ugettext_lazy("Organization related to these permissions"))
    can_add_members = models.BooleanField(default=False)
    can_remove_members = models.BooleanField(default=False)
    can_create_petitions = models.BooleanField(default=False)
    can_modify_petitions = models.BooleanField(default=False)
    can_delete_petitions = models.BooleanField(default=False)
    can_create_templates = models.BooleanField(default=False)
    can_modify_templates = models.BooleanField(default=False)
    can_delete_templates = models.BooleanField(default=False)
    can_view_signatures = models.BooleanField(default=False)
    can_modify_signatures = models.BooleanField(default=False)
    can_delete_signatures = models.BooleanField(default=False)
    can_modify_permissions = models.BooleanField(default=False)

    def __str__(self):
        ret = "{orgname} : ".format(orgname=self.organization.name)
        if self.user.count() > 0:
            ret = ret + "{username}".format(username=self.user.all()[0].name)
        else:
            ret = ret + "None"
        return ret

    def __repr__(self):
        return self.__str__()


class PytitionUser(models.Model):
    petitions = models.ManyToManyField(Petition, blank=True)
    organizations = models.ManyToManyField(Organization, related_name="members", blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pytitionuser")
    permissions = models.ManyToManyField(Permission, related_name="user", blank=True)
    invitations = models.ManyToManyField(Organization, related_name="invited", blank=True)
    petition_templates = models.ManyToManyField(PetitionTemplate, blank=True, through='TemplateOwnership',
                                                through_fields=['user', 'template'],
                                                verbose_name=ugettext_lazy("Petition templates"))
    default_template = models.ForeignKey(PetitionTemplate, blank=True, null=True, related_name='+',
                                         verbose_name=ugettext_lazy("Default petition template"), to_field='id',
                                         on_delete=models.SET_NULL)

    @property
    def is_authenticated(self):
        return self.user.is_authenticated

    @property
    def name(self):
        return self.username

    @property
    def username(self):
        return self.user.username

    @property
    def get_full_name(self):
        return self.user.get_full_name()

    @property
    def fullname(self):
        return self.get_full_name

    @property
    def kind(self):
        return "user"

    def __str__(self):
        return self.get_full_name

    def __repr__(self):
        return self.get_full_name

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        PytitionUser.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    instance.pytitionuser.save()


@receiver(post_delete, sender=PytitionUser)
def post_delete_user(sender, instance, *args, **kwargs):
    if instance.user:  # just in case user is not specified
        instance.user.delete()

class TemplateOwnership(models.Model):
    user = models.ForeignKey(PytitionUser, blank=True, null=True, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, blank=True, null=True, on_delete=models.CASCADE)
    template = models.ForeignKey(PetitionTemplate, to_field='id', on_delete=models.CASCADE)

    def clean(self):
        if self.user is None and self.organization is None:
            raise ValidationError(_("The template needs to be owned by a User or an Organization."
                                    "It cannot hang around alone by itself."))
    #class Meta:
    #    unique_together = (("user", "template"), ("organization", "template"))