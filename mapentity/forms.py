from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django import forms as django_forms

import floppyforms as forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Button, HTML
from crispy_forms.bootstrap import FormActions
from tinymce.widgets import TinyMCE
from modeltranslation.translator import translator, NotRegistered


class MapEntityForm(forms.ModelForm):
    formfield_callback = lambda f: MapEntityForm.make_tinymce_widget(f)

    modelfields = tuple()
    geomfields = tuple()
    actions = FormActions(
        HTML('<!-- delete button -->'),
        Submit('save_changes', _('Save changes'), css_class="btn-primary pull-right offset1"),
        Button('cancel', _('Cancel'), css_class="pull-right offset1"),
        css_class="form-actions",
    )

    pk = forms.Field(required=False, widget=forms.Field.hidden_widget)
    model = forms.Field(required=False, widget=forms.Field.hidden_widget)

    helper = FormHelper()

    class Meta:
        pass

    # TODO: this is obvisouly wrong MapEntity should not depend on core
    # TODO: Django inserts Media in <head> https://code.djangoproject.com/ticket/13978
    MEDIA_JS = ("core/formfield.js",)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(MapEntityForm, self).__init__(*args, **kwargs)

        # Generic behaviour
        if self.instance.pk:
            self.helper.form_action = self.instance.get_update_url()
            # Put delete url in Delete button
            self.actions.fields[0] = HTML('<a class="btn btn-danger delete" href="%s"><i class="icon-white icon-trash"></i> %s</a>' % (
                self.instance.get_delete_url(),
                unicode(_("Delete"))))
        else:
            self.helper.form_action = self.instance.get_add_url()
            # Remove Delete if adding new instance
            self.actions.fields.remove(self.actions.fields[0])

        self.fields['pk'].initial = self.instance.pk
        self.fields['model'].initial = self.instance._meta.module_name

        self.__expand_translatable_fields()

        # Get fields from subclasses
        fields = ('pk', 'model', 'structure') + self.modelfields

        has_geomfield = len(self.geomfields) > 0
        leftpanel = Div(
            *fields,
            css_class="scrollable span" + ('4' if has_geomfield else '12'),
            css_id="modelfields"
        )

        rightpanel = (),
        if has_geomfield:
            rightpanel = Div(
                *self.geomfields,
                css_class="span8",
                css_id="geomfield"
            )

        # Main form layout
        self.helper.help_text_inline = True
        self.helper.form_class = 'form-horizontal'
        self.helper.layout = Layout(
            Div(
                Div(
                    leftpanel,
                    rightpanel,
                    css_class="row-fluid"
                ),
                css_class="container-fluid"
            ),
            self.actions
        )

    @staticmethod
    def make_tinymce_widget(f):
        formfield = f.formfield()
        if formfield and isinstance(formfield.widget, (forms.widgets.Textarea,
                                                       django_forms.widgets.Textarea)):
            formfield.widget = TinyMCE()
        return formfield

    """

    Auto-expand translatable fields.

    """

    def __expand_translatable_fields(self):
        # Expand i18n fields
        try:
            # Obtain model translation options
            mto = translator.get_options_for_model(self._meta.model)
        except NotRegistered:
            # No translation field on this model, nothing to do
            pass
        else:
            for f in mto.fields:
                self.fields.pop(f)
            # Switch to mutable sequence
            self.modelfields = list(self.modelfields)
            for f in mto.fields:
                self.__replace_translatable_field(f, self.modelfields)
            # Switch back to unmutable sequence
            self.modelfields = tuple(self.modelfields)

    def __replace_translatable_field(self, field, modelfields):
        for i, modelfield in enumerate(modelfields):
            if hasattr(modelfield, 'fields'):
                # Switch to mutable sequence
                modelfield.fields = list(modelfield.fields)
                self.__replace_translatable_field(field, modelfield.fields)
                # Switch back to unmutable sequence
                modelfield.fields = tuple(modelfield.fields)
            else:
                if modelfield == field:
                    # Replace i18n field by dynamic l10n fields
                    i = modelfields.index(modelfield)
                    modelfields[i:i + 1] = self.__tabbed_translatable_field(modelfield)

    def __tabbed_translatable_field(self, field):
        fields = []
        for l in settings.LANGUAGES:
            active = "active" if l[0] == settings.LANGUAGE_CODE else ""
            fields.append(Div(
                '%s_%s' % (field, l[0]),
                css_class="tab-pane " + active,
                css_id="%s_%s" % (field, l[0])))

        layout = Div(
            HTML("""
            <ul class="nav nav-pills">
            {% for lang in LANGUAGES %}
                <li {% if lang.0 == LANGUAGE_CODE %}class="active"{% endif %}><a href="#%s_{{ lang.0 }}" data-toggle="tab">{{ lang.0 }}</a></li>
            {% endfor %}
            </ul>
            """.replace("%s", field)),
            Div(
                *fields,
                css_class="tab-content"
            ),
            css_class="tabbable"
        )
        return [layout]
