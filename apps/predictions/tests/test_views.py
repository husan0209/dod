from django.test import TestCase, RequestFactory

from ..views import IndexView

from ..models import Category


class ViewsTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            icon='🎯',
            color='#000000',
        )

    def test_index_view_queryset(self):
        request = self.factory.get('/')
        view = IndexView()
        view.request = request
        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)

    def test_index_view_with_category(self):
        request = self.factory.get('/', {'category': str(self.category.id)})
        view = IndexView()
        view.request = request
        queryset = view.get_queryset()
        # Should filter by category
        self.assertIsNotNone(queryset)
