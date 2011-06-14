import os

from django.core.files import File

from nose.tools import eq_

from groups.models import GroupProfile
from groups.tests import group_profile
from sumo.tests import TestCase
from sumo.urlresolvers import reverse
from users.tests import user, group, add_permission


class EditGroupProfileTests(TestCase):
    def setUp(self):
        super(EditGroupProfileTests, self).setUp()
        self.user = user(save=True)
        self.group_profile = group_profile(group=group(save=True), save=True)
        self.client.login(username=self.user.username, password='testpass')

    def _verify_get_and_post(self):
        slug = self.group_profile.slug
        # Verify GET
        r = self.client.get(reverse('groups.edit', args=[slug]), follow=True)
        eq_(r.status_code, 200)
        # Verify POST
        r = self.client.post(reverse('groups.edit', locale='en-US',
                                     args=[slug]),
                             {'information': '=new info='})
        eq_(r.status_code, 302)
        gp = GroupProfile.uncached.get(slug=slug)
        eq_(gp.information, '=new info=')

    def test_edit_with_perm(self):
        add_permission(self.user, GroupProfile, 'change_groupprofile')
        self._verify_get_and_post()

    def test_edit_as_leader(self):
        self.group_profile.leaders.add(self.user)
        self._verify_get_and_post()

    def test_edit_without_perm(self):
        slug = self.group_profile.slug
        # Try GET
        r = self.client.get(reverse('groups.edit', args=[slug]), follow=True)
        eq_(r.status_code, 403)
        # Try POST
        r = self.client.post(reverse('groups.edit', locale='en-US',
                                     args=[slug]),
                             {'information': '=new info='})
        eq_(r.status_code, 403)


class EditAvatarTests(TestCase):
    def setUp(self):
        super(EditAvatarTests, self).setUp()
        self.user = user(save=True)
        add_permission(self.user, GroupProfile, 'change_groupprofile')
        self.group_profile = group_profile(group=group(save=True), save=True)
        self.client.login(username=self.user.username, password='testpass')

    def tearDown(self):
        if self.group_profile.avatar:
            self.group_profile.avatar.delete()
        super(EditAvatarTests, self).tearDown()

    def test_upload_avatar(self):
        """Upload a group avatar."""
        with open('apps/upload/tests/media/test.jpg') as f:
            self.group_profile.avatar.save('test_old.jpg', File(f), save=True)
        assert self.group_profile.avatar.name.endswith('92b516.jpg')
        old_path = self.group_profile.avatar.path
        assert os.path.exists(old_path), 'Old avatar is not in place.'

        url = reverse('groups.edit_avatar', locale='en-US',
                      args=[self.group_profile.slug])
        with open('apps/upload/tests/media/test.jpg') as f:
            r = self.client.post(url, {'avatar': f})

        eq_(302, r.status_code)
        url = reverse('groups.profile', args=[self.group_profile.slug])
        eq_('http://testserver/en-US' + url, r['location'])
        assert not os.path.exists(old_path), 'Old avatar was not removed.'

    def test_delete_avatar(self):
        """Delete a group avatar."""
        self.test_upload_avatar()

        url = reverse('groups.delete_avatar', locale='en-US',
                      args=[self.group_profile.slug])
        r = self.client.get(url)
        eq_(200, r.status_code)
        r = self.client.post(url)
        eq_(302, r.status_code)
        url = reverse('groups.profile', args=[self.group_profile.slug])
        eq_('http://testserver/en-US' + url, r['location'])
        gp = GroupProfile.uncached.get(slug=self.group_profile.slug)
        eq_('', gp.avatar.name)