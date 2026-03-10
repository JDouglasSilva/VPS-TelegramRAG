import os
import django
from django.test import TestCase
from django.contrib.auth.models import User
from core_api.models import Organization, Member

class OrganizationMemberTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.org1 = Organization.objects.create(name='Org Alpha', admin=self.user1)
        self.org2 = Organization.objects.create(name='Org Beta', admin=self.user2)

    def test_create_member_successfully(self):
        member = Member.objects.create(user=self.user1, organization=self.org1, role=Member.Role.ADMIN)
        self.assertEqual(member.organization, self.org1)
        self.assertEqual(member.role, 'ADMIN')

    def test_user_cannot_be_in_two_organizations(self):
        # Cria primeiro membro
        Member.objects.create(user=self.user1, organization=self.org1, role=Member.Role.ADMIN)
        
        # Tenta colocar o MESMO usuário em outra organização (deve lançar exceção de integridade pelo OneToOneField)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Member.objects.create(user=self.user1, organization=self.org2, role=Member.Role.USER)
