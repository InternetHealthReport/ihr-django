from .const import ConfirmationEmail, ResetPasswordEmail, StrErrors
from .utility import account_activation_token, google_token_verification, parse_request, std_response, EmailChangeTokenGenerator, IHRException
from .serializers import IHRUserSerializer
from ..models import IHRUser, MonitoredASN, ASN, UserManager, EmailChangeRequest
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_410_GONE,
    HTTP_409_CONFLICT,
    HTTP_200_OK
)
from django.core.mail import send_mail
from smtplib import SMTPException
from email.errors import HeaderParseError
import json
from django.db import transaction, IntegrityError
from datetime import datetime
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from itertools import islice

class UserView(viewsets.GenericViewSet):
    queryset = IHRUser.objects
    serializer_class = IHRUserSerializer

    @action(detail=False, methods=["POST"], permission_classes=[AllowAny])
    def sign_in(self, request):
        content = parse_request(request)
        try:
            google_token_verification(content)
            with transaction.atomic():
                user = self.get_queryset().create_user(content["email"], content["password"])
                token = account_activation_token.make_token(user)
                confirmation_email = ConfirmationEmail(user.email, token)
                send_mail(
                    'Account activation',
                    confirmation_email.PLAIN,
                    'noreplay@ihr.iij.jp',
                    [user.email],
                    fail_silently=False,
                )
        except IntegrityError as e:
            return std_response(StrErrors.DUPLICATED, HTTP_409_CONFLICT)
        except (ValueError, SMTPException, HeaderParseError, KeyError) as e:
            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
        return Response(status=HTTP_200_OK)

    @action(detail=False, methods=["POST"], permission_classes=[AllowAny])
    def validate(self, request):
        content = parse_request(request)
        try:
            with transaction.atomic():
                user = self.get_queryset().get(email=content["email"])
                if not user.check_password(content["password"]):
                    return std_response(StrErrors.WRONG_DATA, HTTP_403_FORBIDDEN)
                if user.is_active:
                    return std_response(StrErrors.ALREADY_VALIDATED, HTTP_409_CONFLICT)
                if not account_activation_token.check_token(user, content["token"]):
                    return std_response(StrErrors.WRONG_DATA, HTTP_403_FORBIDDEN)
                user.is_active = True
                user.save()
        except (KeyError, IHRUser.DoesNotExist)  as e:
            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
        return self.login(request)

    @action(detail=False, methods=['POST'], permission_classes=[IsAuthenticated])
    def sign_out(self, request):
        request.user.delete()
        return Response(status=HTTP_200_OK)

    @action(detail=False, methods=["POST"], permission_classes=[AllowAny])
    def login(self, request):
        content = parse_request(request)
        try:
            with transaction.atomic():
                user = self.get_queryset().get(email=content["email"])
                if not user.is_active and not user.check_password(content["password"]):
                    return std_response(StrErrors.WRONG_DATA, HTTP_403_FORBIDDEN)
                user.last_login = datetime.utcnow()
                user.save()
                token,_ = Token.objects.get_or_create(user=user)
        except (KeyError, IHRUser.DoesNotExist)  as e:
            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
        return Response({'token': token.key}, status=HTTP_200_OK)

    @action(detail=False, methods=['POST'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        request.user.auth_token.delete()
        return Response(status=HTTP_200_OK)

    @action(detail=False, methods=["POST"], permission_classes=[AllowAny])
    def request_reset_password(self, request):
        content = parse_request(request)
        try:
            user = self.get_queryset().get(email=content["email"])
            google_token_verification(content)
            token = account_activation_token.make_token(user)
            reset_email = ResetPasswordEmail(user.email, token)
            send_mail(
                'Account activation',
                reset_email.PLAIN,
                'noreplay@ihr.iij.jp',
                [user.email],
                fail_silently=False,
            )
        except IHRUser.DoesNotExist as e:
            return std_response(StrErrors.WRONG_DATA, HTTP_403_FORBIDDEN)
        except (ValueError, SMTPException, HeaderParseError, KeyError) as e:
            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
        return Response(status=HTTP_200_OK)

    @action(detail=False, methods=["POST"], permission_classes=[AllowAny])
    def reset_password(self, request):
        content = parse_request(request)
        try:
            with transaction.atomic():
                user = self.get_queryset().get(email=content["email"])
                if not account_activation_token.check_token(user, content["token"]):
                    return std_response(StrErrors.WRONG_DATA, HTTP_403_FORBIDDEN)
                user.set_password(content["password"])
                user.save()
        except (KeyError, IHRUser.DoesNotExist)  as e:
            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
        return self.login(request)

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def verify_token(self, request):
        return Response(status=HTTP_200_OK)

    @action(detail=False, methods=["POST"], permission_classes=[IsAuthenticated])
    def change_credentials(self, request):
        email = request.data.get("email")
        if email is not None:
            #change email
            if self.get_queryset().filter(email=email).count() > 0:
                return std_response(StrErrors.DUPLICATED, HTTP_409_CONFLICT)
            try:
                change = EmailChangeRequest(user=request.user, new_email=email)
                change.save()
                token_checker = EmailChangeTokenGenerator(change.new_email, change.request_time)
                token = token_checker.make_token(request.user)
                reset_email = ConfirmationEmail(change.new_email, token, password_change=True)
                send_mail(
                    'Email change',
                    reset_email.PLAIN,
                    'noreplay@ihr.iij.jp',
                    [change.new_email],
                    fail_silently=False,
                )
            except (SMTPException, HeaderParseError) as e:
                return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)

        password = request.data.get("password")
        if password is not None:
            #change password
            request.user.set_password(password)
            request.user.save()

        return Response(status=HTTP_200_OK)

    @action(detail=False, methods=["POST"], permission_classes=[AllowAny])
    def change_email(self, request):
        content = parse_request(request)
        #import pdb; pdb.set_trace()
        try:
            change  = EmailChangeRequest.objects.get(new_email=content["email"])
            user = change.user
            if not user.is_active or not user.check_password(content["password"]):
                return std_response(StrErrors.WRONG_DATA, HTTP_403_FORBIDDEN)

            now = datetime.utcnow()
            if (now - change.request_time.replace(tzinfo=None)).days * 24 * 60 > EmailChangeRequest.VALIDITY:
                raise IHRException(status_code=HTTP_410_GONE, message=StrErrors.WRONG_DATA, log=False)

            if self.get_queryset().filter(email=content["email"]).count() > 0:
                raise IHRException(status_code=HTTP_409_CONFLICT, message=StrErrors.DUPLICATED, log=False)

            token_checker = EmailChangeTokenGenerator(change.new_email, change.request_time)
            if token_checker.check_token(user, content["token"]):
                user.email = change.new_email
                user.save()
                change.delete()
                return self.login(request)
        except (KeyError, EmailChangeRequest.DoesNotExist) as e:
            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST,)
        except IHRException as e:
            change.delete()
            raise e
        return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["POST"], permission_classes=[IsAuthenticated])
    def show(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(detail=False, methods=["POST"], permission_classes=[IsAuthenticated])
    def add_monitoring(self, request):
        monitored_asn = request.data.get("monitoredasn")
        if not monitored_asn:
            return std_response(StrErrors.INPUT.ADD_MONITORING, HTTP_400_BAD_REQUEST)
        asn_list = []
        for i, monitored in enumerate(monitored_asn):
            for j in range(i + 1, len(monitored_asn)):
                if monitored["asnumber"] == monitored_asn[j]["asnumber"]:
                    return std_response(StrErrors.INPUT.DUPLICATED, HTTP_400_BAD_REQUEST)
            asn_list.append(monitored["asnumber"])

        monitored_update, batch = [], []
        try:
            already_monitored = MonitoredASN.objects.filter(user=request.user)
            already_monitored.all().exclude(asn__in=asn_list).delete()
            with transaction.atomic():
                for monitored in monitored_asn:
                    for i, am in enumerate(already_monitored):
                        print("here", am)
                        if am.asn.number == monitored["asnumber"]:
                            am.notifylevel = monitored["notifylevel"]
                            am.save()
                            print(am.asn.number, "save")
                            break
                    else: #if it's not an update is a new monitor
                        print(monitored["asnumber"], "bulk")
                        batch.append(MonitoredASN(user=request.user, asn=ASN.objects.get(number=monitored["asnumber"]), notifylevel=monitored["notifylevel"]))

                MonitoredASN.objects.bulk_create(batch)
        except ASN.DoesNotExist as e:
            return std_response(StrErrors.ASN_DOESNOT_EXIST, HTTP_400_BAD_REQUEST)
        return Response(status=HTTP_200_OK)
