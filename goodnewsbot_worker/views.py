from django.views.generic import TemplateView


class LandingView(TemplateView):
    """Render static landing page template"""
    template_name = 'landing.html'
