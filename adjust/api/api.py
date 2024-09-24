#!/usr/bin/env python
from __future__ import annotations
from functools import cached_property
import json
import os
from types import NoneType
from bs4 import BeautifulSoup
from pydantic import parse_obj_as
from typing import Any, Optional, Type, TypeVar

import requests

from .model import RawCallback, App, AppsResponse, Callback, Event, EventsResponse, Placeholder, User, UserToken


T = TypeVar("T")


class AdjustAPI(object):
    """A class to interact with the Adjust API

    Attributes:
        user : User
            The currently logged in user
        placeholders : list[Placeholder]
            A list of all the available Adjust placeholders
        apps : list[App]
            The list of all the registered apps on the Adjust dashboard
            The app object contains attributes such as the adjust token or the platform
            appIds

    Methods:
        events(app: App | str) : list[Event]
            Get the list of all the events registered for an App or app token
        callbacks(app: App | str) : list[Callback]
            Get the list of all the available callbacks for an App or app token.
            The returned Callback objects contain the endpoint URL if one is set.
        set_callback(app: App | str, type: str, callback_url: str)
            Updates the callback of a given type to the new callback_url.

    """

    def __init__(self, email: str = None, password: str = None):
        """Creates an object that can be used to issue calls to the Adjust API.
        Valid credentials must be supplied in order for the API calls to be
        authenticated and authorized.

        Args:
            email (str): the authentication email
            password (str): the authentication password
        """
        email = email or os.getenv("ADJUST_EMAIL")
        if not email:
            raise ValueError("Email not provided")
        password = password or os.getenv("ADJUST_PASSWORD")
        if not password:
            raise ValueError("Password not provided")
        self._session = requests.Session()
        self._user: Optional[User] = None
        self._log_in = lambda: self._sign_in(email, password)
        self._logged_in = False

    def _log_in_if_needed(self) -> None:
        """Internal method used to log in upon first use"""
        if not self._logged_in:
            self._logged_in = True
            self._log_in()

    def _api(self, type: Type[T], path: str, method: str = "GET", **data: Any) -> T:
        """Internal method used to emit low-level API calls.

        Args:
            path (str): the API path to call
            method (str, optional): The HTTP method to use. Defaults to "GET".

        Returns:
            Any: the API response
        """
        self._log_in_if_needed()
        url = "https://api.adjust.com/" + path
        # Default headers
        headers = {"Accept": "application/json"}

        # If logging in, add the authorization token to the headers
        if path == "accounts/users/sign_in" and data['user']['email'] == "gpereyra@jamcity.com":
            token = data['user']['password']
            headers["Authorization"] = f"Token token={token}"
            userEmail = data['user']['email']
            data = None
            
        if not data:
            r = self._session.get(url, headers=headers)
        elif method == "PUT":
            r = self._session.put(url, headers=headers, json=data)
        else:
            r = self._session.post(url, headers=headers, json=data)
        r.raise_for_status()
        # Verificar si el usuario debe ser transformado
        if r.status_code == 200 and path == "accounts/users/sign_in" and userEmail == "gpereyra@jamcity.com":
            # Crear un diccionario del user
            user_data = {'id': '10', 'email': userEmail, 'name': 'Admin'}
            user_token = UserToken(id=int(user_data['id']), email=user_data['email'], name=user_data['name'])
            user = user_token_to_user(user_token)
            return parse_obj_as(type, user)

        return parse_obj_as(type, None if r.status_code == 204 else r.json())

    def _sign_in(self, email: str, password: str) -> None:
        """Internal method to authenticate with the Adjust API

        Args:
            email (str): The login email
            password (str): The login password

        Returns:
            User: The logged in user
        """
        user = dict(email=email, password=password, remember_me=True)
        self._user = self._api(User, "accounts/users/sign_in", user=user)

    def user(self) -> Optional[User]:
        """Returns the currently logged in user

        Returns:
            User
        """
        self._log_in_if_needed()
        return self._user

    @cached_property
    def placeholders(self) -> list[Placeholder]:
        """Returns a list of all available Adjust placeholders

        Returns:
            list[Placeholder]
        """
        url = "https://help.adjust.com/en/partner/placeholders"
        html = self._session.get(url).content
        soup = BeautifulSoup(html, "lxml")
        script = soup.find(id="__NEXT_DATA__")
        assert script, "Could not find placeholders data"
        data = json.loads(script.text)
        placeholders = data["props"]["pageProps"]["placeholdersData"]
        return [Placeholder.parse_obj(p) for p in placeholders]

    @cached_property
    def apps(self) -> list[App]:
        """Returns a list of all the registered apps on the Adjust dashboard.
        The returned list contains one object per application, with properties
        such as the app token or platform appIds.

        Returns:
            list[App]
        """
        response = self._api(AppsResponse, "dashboard/api/apps")
        return response.apps

    def callbacks(self, app: App | str) -> list[Callback]:
        """Returns the list of callbacks available for an app or app token.

        Args:
            app (App | str): the app or app token

        Returns:
            list[Callback]: the callback mapping
        """
        token = app if isinstance(app, str) else app.token
        cbs = self._api(list[RawCallback], f"dashboard/api/apps/{token}/callbacks")
        return [c.to_callback() for c in cbs]

    def events(self, app: App | str, include_archived: bool = False) -> dict[str, Event]:
        """Returns a mapping of all the events for an app or app token.
        Events are mapped by their event token.

        Args:
            app (App | str): The app or app token
            include_archived (bool, optional): True to include archived events.
                                               Defaults to False.

        Returns:
            list[Event]: the list of events
        """
        token = app if isinstance(app, str) else app.token
        template = f"dashboard/api/apps/{token}/event_types?include_archived={include_archived}"  # noqa: E501
        data = self._api(EventsResponse, template)
        return {e.token: e for e in data.events}

    def update_callback(self, app: App | str, callback: Callback) -> None:
        """Updates an app callback.

        Args:
            app (App | str): The app or app token
            callback (Callback): The modified callback to be updated
        """
        token = app if isinstance(app, str) else app.token
        path = f"dashboard/api/apps/{token}/event_types/{callback.id}/callback"
        self._api(NoneType, path, method="PUT", callback_url=callback.url)
        
    def user_token_to_user(user_token: UserToken) -> User:
        """Transforms a UserToken object into a User object.
    
        Args:
            user_token (UserToken): The UserToken instance containing minimal user information.
    
        Returns:
            User: A new User instance populated with values from the UserToken and default values
            for the missing fields.
        """
        return User(
            id=user_token.id,
            email=user_token.email,
            name=user_token.name,
            main_account_id=0,  
            main_account_type="",  
            created_by=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            authentication_token="",
            locale='en',
            uses_next=False,
            api_access=None,
            first_name="",
            last_name="",
            super_admin=False,
            salesforce_sync_failed=False,
            ct_role=None,
            timezone_id=0,
            uses_dash=False,
            sso=False,
            direct_otp=None,
            direct_otp_sent_at=None,
            encrypted_otp_secret_key=None,
            encrypted_otp_secret_key_iv=None,
            encrypted_otp_secret_key_salt=None
        )