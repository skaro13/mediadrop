from tg import request
from tg.decorators import expose, validate
from repoze.what.predicates import has_permission
from pylons import tmpl_context

from mediacore.lib.base import BaseController
from mediacore.lib.helpers import expose_xhr, paginate, redirect, url_for
from mediacore.model import DBSession, fetch_row
from mediacore.model.auth import User, Group
from mediacore.forms.users import UserForm

user_form = UserForm()


class UseradminController(BaseController):
    """Admin user actions"""
    allow_only = has_permission('admin')

    @expose_xhr('mediacore.templates.admin.users.index',
                'mediacore.templates.admin.users.index-table')
    @paginate('users', items_per_page=50)
    def index(self, page=1, **kwargs):
        """List users with pagination.

        :param page: Page number, defaults to 1.
        :type page: int
        :rtype: Dict
        :returns:
            users
                The list of :class:`~mediacore.model.auth.User`
                instances for this page.

        """
        users = DBSession.query(User).order_by(User.display_name,
                                               User.email_address)
        return dict(users=users)


    @expose('mediacore.templates.admin.users.edit')
    def edit(self, id, **kwargs):
        """Display the :class:`~mediacore.forms.users.UserForm` for editing or adding.

        :param id: User ID
        :type id: ``int`` or ``"new"``
        :rtype: dict
        :returns:
            user
                The :class:`~mediacore.model.auth.User` instance we're editing.
            user_form
                The :class:`~mediacore.forms.users.UserForm` instance.
            user_action
                ``str`` form submit url
            user_values
                ``dict`` form values

        """
        user = fetch_row(User, id)

        if tmpl_context.action == 'save' or id == 'new':
            # Use the values from error_handler or GET for new users
            user_values = kwargs
            user_values['login_details.password'] = None
            user_values['login_details.confirm_password'] = None
        else:
            user_values = dict(
                display_name = user.display_name,
                email_address = user.email_address,
                login_details = dict(
                    group = user.groups[0].group_id if user.groups else None,
                    user_name = user.user_name,
                ),
            )

        return dict(
            user = user,
            user_form = user_form,
            user_action = url_for(action='save'),
            user_values = user_values,
        )


    @expose()
    @validate(user_form, error_handler=edit)
    def save(self, id, email_address, display_name, login_details,
             delete=None, **kwargs):
        """Save changes or create a new :class:`~mediacore.model.auth.User` instance.

        :param id: User ID. If ``"new"`` a new user is created.
        :type id: ``int`` or ``"new"``
        :returns: Redirect back to :meth:`index` after successful save.

        """
        user = fetch_row(User, id)

        if delete:
            DBSession.delete(user)
            redirect(action='index', id=None)

        user.display_name = display_name
        user.email_address = email_address
        user.user_name = login_details['user_name']

        password = login_details['password']
        if password is not None and password != '':
            user.password = password

        if login_details['group']:
            group = fetch_row(Group, login_details['group'])
            user.groups = [group]
        else:
            user.groups = []

        DBSession.add(user)
        DBSession.flush()
        redirect(action='index', id=None)


    @expose('json')
    def delete(self, id, **kwargs):
        """Delete a user.

        :param id: User ID.
        :type id: ``int``
        :returns: Redirect back to :meth:`index` after successful delete.
        """
        user = fetch_row(User, id)
        DBSession.delete(user)

        if request.is_xhr:
            return dict(success=True)
        redirect(action='index', id=None)