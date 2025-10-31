from home.models import HomePage

from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase


class HomeSetUpTests(WagtailPageTestCase):
    """
    Tests for basic page structure setup and HomePage creation.
    """

    def test_root_create(self):
        root_page = Page.objects.get(pk=1)
        self.assertIsNotNone(root_page)

    def test_homepage_create(self):
        root_page = Page.objects.get(pk=1)
        homepage = HomePage(title="Home")
        root_page.add_child(instance=homepage)
        self.assertTrue(HomePage.objects.filter(title="Home").exists())


class HomeTests(WagtailPageTestCase):
    """
    Tests for homepage functionality and rendering.
    """

    def setUp(self):
        """
        Create a homepage instance for testing.
        """
        root_page = Page.get_first_root_node()
        Site.objects.create(hostname="testsite", root_page=root_page, is_default_site=True)
        self.homepage = HomePage(title="Home")
        root_page.add_child(instance=self.homepage)

    def test_homepage_is_renderable(self):
        self.assertPageIsRenderable(self.homepage)

    def test_homepage_template_used(self):
        response = self.client.get(self.homepage.url)
        self.assertTemplateUsed(response, "home/home_page.html")




from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, Group
from django.contrib.sessions.middleware import SessionMiddleware
from wagtail.models import BaseViewRestriction
from wagtail.models import Page, PageViewRestriction

class ViewRestrictionMCDCTests(TestCase):


    def setUp(self):
        self.factory = RequestFactory()
        # cria página raiz e página filha para anexar a restrição
        self.root = Page.get_first_root_node()
        self.page = self.root.add_child(instance=Page(title="Privada", slug="privada"))

    def _build_request(self, user=None):
        from django.contrib.auth.models import AnonymousUser

        req = self.factory.get("/")
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(req)
        req.session.save()
        req.user = user if user is not None else AnonymousUser()
        return req

    # CT-P1: C1 = F -> negar (sessão NÃO contém o pvr.id)
    def test_password_denied_without_session(self):
        pvr = PageViewRestriction.objects.create(
            page=self.page,
            restriction_type=PageViewRestriction.PASSWORD,
            password="senha",
        )
        req = self._build_request()
        self.assertFalse(pvr.accept_request(req))

    # CT-P2: C1 = T -> permitir (sessão contém o pvr.id)
    def test_password_allowed_with_session(self):
        pvr = PageViewRestriction.objects.create(
            page=self.page,
            restriction_type=PageViewRestriction.PASSWORD,
            password="senha",
        )
        user = User.objects.create_user("u_pwd", password="x")
        req = self._build_request(user)
        key = pvr.passed_view_restrictions_session_key
        req.session[key] = [pvr.id]
        req.session.save()
        self.assertTrue(pvr.accept_request(req))

    # CT-L1: C2 = F -> negar (user anônimo)
    def test_login_required_denied_when_anonymous(self):
        pvr = PageViewRestriction.objects.create(
            page=self.page,
            restriction_type=PageViewRestriction.LOGIN,
        )
        req = self._build_request()
        self.assertFalse(pvr.accept_request(req))

    # CT-L2: C2 = T -> permitir (user autenticado)
    def test_login_required_allowed_when_authenticated(self):
        pvr = PageViewRestriction.objects.create(
            page=self.page,
            restriction_type=PageViewRestriction.LOGIN,
        )
        user = User.objects.create_user("u_login", password="x")
        req = self._build_request(user)
        self.assertTrue(pvr.accept_request(req))

    # CT-G1: C3=T, C4=T -> permitir (autenticado e membro do Group)
    def test_groups_allowed_when_authenticated_and_in_group(self):
        pvr = PageViewRestriction.objects.create(
            page=self.page,
            restriction_type=PageViewRestriction.GROUPS,
        )
        # avoid UNIQUE constraint errors if a Group with this name already exists
        g, _ = Group.objects.get_or_create(name="Editors")
        pvr.groups.add(g)

        u1 = User.objects.create_user("u1_group", password="x")
        u1.groups.add(g)
        req1 = self._build_request(u1)
        self.assertTrue(pvr.accept_request(req1))

    # CT-G2: C3=T, C4=F -> negar (autenticado, fora dos grupos permitidos)
    def test_groups_denied_when_authenticated_but_not_in_group(self):
        pvr = PageViewRestriction.objects.create(
            page=self.page,
            restriction_type=PageViewRestriction.GROUPS,
        )
        # reuse existing group if present
        g, _ = Group.objects.get_or_create(name="Editors")
        pvr.groups.add(g)

        u2 = User.objects.create_user("u2_no_group", password="x")
        req2 = self._build_request(u2)
        self.assertFalse(pvr.accept_request(req2))

    # CT-G3: C3=F, C4=T -> negar (anônimo mesmo com grupo definido)
    def test_groups_denied_when_anonymous_even_if_group_exists(self):
        pvr = PageViewRestriction.objects.create(
            page=self.page,
            restriction_type=PageViewRestriction.GROUPS,
        )
        # reuse existing group if present
        g, _ = Group.objects.get_or_create(name="Editors")
        pvr.groups.add(g)

        req3 = self._build_request()  # AnonymousUser
        self.assertFalse(pvr.accept_request(req3))


# Tutorial pra rodar os testes e receber relatório usando o coverage
# Rodar:
#   python manage.py test home
#   coverage run --source=wagtail,. manage.py test home
#   coverage html
# Abrir:
#   htmlcov/index.html
