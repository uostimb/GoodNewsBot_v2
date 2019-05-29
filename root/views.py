from django.views.generic import TemplateView


class RootView(TemplateView):
    """Render static landing page template"""
    template_name = 'root.html'
