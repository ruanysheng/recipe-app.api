"""
Test for the tags API.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal
from core.models import Tag, Recipe

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    '''Create and return a tag detail url.'''
    return reverse('recipe:tag-detail', args=[tag_id])

def create_user(email='user@example.com', password='testpass123'):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagsApiTests(TestCase):
    '''Test unauthenticated APPI requests.'''

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        '''Test auth is required for retrieving tags.'''
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    '''Test authenticated API requests.'''
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        '''Test retreiving a list of tags.'''
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        '''Test list of tags is limited to authencated user.'''
        user2 = create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name='Fruity')
        tag = Tag.objects.create(user=self.user, name='Comfort Food')

        res = self.client.get(TAGS_URL)

        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEquals(len(res.data), 1)
        self.assertEquals(res.data[0]['name'], tag.name)
        self.assertEquals(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        '''Test update tag.'''
        tag = Tag.objects.create(user=self.user, name='After Dinner')
        payload = {'name': 'Dessert'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)


        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        '''Delete tag'''
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        '''Test listing tags to those assigned to recipes'''
        tag1 = Tag.objects.create(user=self.user, name='Breakfast')
        tag2 = Tag.objects.create(user=self.user, name='Lunch')
        recipe = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
            user=self.user,
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        '''Test filtered tags returns a unique list.'''
        tag = Tag.objects.create(user=self.user, name='Lunch')
        Tag.objects.create(user=self.user, name='DInner')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Herb Eggs',
            time_minutes=20,
            price=Decimal('4.00'),
            user=self.user,
        )
        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)