import os
from typing import List, Union
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType


class EmailConfig:
    def __init__(
        self,
        SMTP_HOST: str,
        SMTP_PORT: int,
        SMTP_USERNAME: str,
        SMTP_PASSWORD: str,
        SMTP_USE_TLS: bool,
        SMTP_USE_SSL: bool,
        MAIL_FROM: str,
    ):
        self.SMTP_HOST = SMTP_HOST
        self.SMTP_PORT = SMTP_PORT
        self.SMTP_USERNAME = SMTP_USERNAME
        self.SMTP_PASSWORD = SMTP_PASSWORD
        self.SMTP_USE_TLS = SMTP_USE_TLS
        self.SMTP_USE_SSL = SMTP_USE_SSL
        self.MAIL_FROM = MAIL_FROM

    @classmethod
    def from_env(cls) -> "EmailConfig":
        app_env = os.getenv("APP_ENV", "development").lower()
        if app_env == "development":
            # Default to Mailpit configuration
            return cls(
                SMTP_HOST=os.getenv("SMTP_HOST", "mailpit"),
                SMTP_PORT=int(os.getenv("SMTP_PORT", "1025")),
                SMTP_USERNAME=os.getenv("SMTP_USERNAME", ""),
                SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
                SMTP_USE_TLS=os.getenv("SMTP_USE_TLS", "false").lower()
                == "true",
                SMTP_USE_SSL=os.getenv("SMTP_USE_SSL", "false").lower()
                == "true",
                MAIL_FROM=os.getenv("MAIL_FROM", "alerts@nbd-wetland.org"),
            )
        else:
            # Enforce production SMTP settings configuration
            return cls(
                SMTP_HOST=os.getenv("SMTP_HOST", ""),
                SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
                SMTP_USERNAME=os.getenv("SMTP_USERNAME", ""),
                SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
                SMTP_USE_TLS=os.getenv("SMTP_USE_TLS", "true").lower()
                == "true",
                SMTP_USE_SSL=os.getenv("SMTP_USE_SSL", "false").lower()
                == "true",
                MAIL_FROM=os.getenv("MAIL_FROM", ""),
            )


class EmailService:
    def __init__(self, config: EmailConfig = None):
        self.config = config or EmailConfig.from_env()
        self.fastmail_config = ConnectionConfig(
            MAIL_USERNAME=self.config.SMTP_USERNAME,
            MAIL_PASSWORD=self.config.SMTP_PASSWORD,
            MAIL_FROM=self.config.MAIL_FROM,
            MAIL_PORT=self.config.SMTP_PORT,
            MAIL_SERVER=self.config.SMTP_HOST,
            MAIL_FROM_NAME="NBD Monitoring Platform",
            MAIL_STARTTLS=self.config.SMTP_USE_TLS,
            MAIL_SSL_TLS=self.config.SMTP_USE_SSL,
            USE_CREDENTIALS=bool(self.config.SMTP_USERNAME),
            VALIDATE_CERTS=True,
        )

    async def send_email_async(
        self,
        to: Union[str, List[str]],
        subject: str,
        html_body: str,
        text_body: str = None,
    ) -> bool:
        recipients = [to] if isinstance(to, str) else to

        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=html_body,
            subtype=MessageType.html,
        )

        fm = FastMail(self.fastmail_config)
        await fm.send_message(message)
        return True

    async def send_alert_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        status_message: str,
        description: str,
        alert_level: str = "danger",  # danger, warning, info
        details_headers: List[str] = None,
        details_table: List[List[str]] = None,
        traceback: str = None,
        action_url: str = "http://localhost:3000/admin/data",
    ) -> bool:
        from jinja2 import Template
        import datetime

        template_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(
            template_dir, "templates", "email", "alert_template.html"
        )

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
        except FileNotFoundError:
            # Fallback inline template in case file isn't found
            template_content = """
            <html><body>
            <h2>{{ subject }}</h2>
            <p><strong>Status:</strong> {{ status_message }}</p>
            <p>{{ description }}</p>
            {% if traceback %}<pre>{{ traceback }}</pre>{% endif %}
            </body></html>
            """

        template = Template(template_content)
        rendered_html = template.render(
            subject=subject,
            status_message=status_message,
            description=description,
            alert_level=alert_level,
            details_headers=details_headers,
            details_table=details_table,
            traceback=traceback,
            action_url=action_url,
            app_env=os.getenv("APP_ENV", "development"),
            timestamp=datetime.datetime.utcnow().strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
        )

        return await self.send_email_async(to, subject, rendered_html)

    async def send_invite_email(
        self,
        to: str,
        role: str,
        invited_by: str = None,
        login_url: str = "http://localhost:3000/login",
    ) -> bool:
        from jinja2 import Template

        template_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(
            template_dir, "templates", "email", "invite_template.html"
        )

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
        except FileNotFoundError:
            # Fallback inline template
            template_content = """
            <html><body>
            <h2>You're invited to NBD Platform</h2>
            <p>You have been invited as a {{ role }}.</p>
            <p><a href="{{ login_url }}">Sign in</a></p>
            </body></html>
            """

        template = Template(template_content)
        rendered_html = template.render(
            email=to,
            role=role,
            invited_by=invited_by,
            login_url=login_url,
        )

        subject = "You're invited to NBD Wetland Monitoring Platform"
        return await self.send_email_async(to, subject, rendered_html)
