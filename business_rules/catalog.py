"""Business-specific products, actions, and default entitlements.

This catalog is intentionally small and concrete for the current business:
ZATCA document generator, typing test, chat app, and blog. The admin-control
platform can read the API contract and manage overrides without knowing billing
provider details.
"""

BUSINESS_PRODUCTS = {
    "zatca": {
        "name": "ZATCA Document Generator",
        "description": "Document, PDF/XML, QR, template, and business-profile limits.",
        "actions": {
            "generate_document": {
                "required": "zatca.enabled",
                "limit": "zatca.documents_per_month",
                "period": "month",
                "usage_event": "zatca.document_generated",
            },
            "export_pdf": {"required": "zatca.pdf_export", "period": "none"},
            "export_xml": {"required": "zatca.xml_export", "period": "none"},
            "generate_qr": {"required": "zatca.qr_generation", "period": "none"},
            "use_premium_template": {"required": "zatca.templates_premium", "period": "none"},
            "create_business_profile": {
                "required": "zatca.enabled",
                "limit": "zatca.business_profiles_limit",
                "period": "total",
                "usage_event": "zatca.business_profile_created",
            },
        },
        "plans": {
            "zatca-free": {
                "name": "ZATCA Free",
                "price_cents": 0,
                "entitlements": {
                    "zatca.enabled": True,
                    "zatca.documents_per_month": 5,
                    "zatca.pdf_export": True,
                    "zatca.xml_export": False,
                    "zatca.qr_generation": True,
                    "zatca.templates_premium": False,
                    "zatca.business_profiles_limit": 1,
                    "zatca.archive_months": 1,
                },
            },
            "zatca-starter": {
                "name": "ZATCA Starter",
                "price_cents": 999,
                "entitlements": {
                    "zatca.enabled": True,
                    "zatca.documents_per_month": 100,
                    "zatca.pdf_export": True,
                    "zatca.xml_export": True,
                    "zatca.qr_generation": True,
                    "zatca.templates_premium": False,
                    "zatca.business_profiles_limit": 1,
                    "zatca.archive_months": 12,
                },
            },
            "zatca-pro": {
                "name": "ZATCA Pro",
                "price_cents": 2499,
                "entitlements": {
                    "zatca.enabled": True,
                    "zatca.documents_per_month": 1000,
                    "zatca.pdf_export": True,
                    "zatca.xml_export": True,
                    "zatca.qr_generation": True,
                    "zatca.templates_premium": True,
                    "zatca.business_profiles_limit": 5,
                    "zatca.archive_months": 60,
                },
            },
        },
    },
    "typing": {
        "name": "Typing Test",
        "description": "Typing tests, certificates, custom lessons, leaderboards, and analytics.",
        "actions": {
            "start_test": {"required": "typing.enabled", "limit": "typing.tests_per_day", "period": "day", "usage_event": "typing.test_started"},
            "complete_test": {"required": "typing.enabled", "period": "none", "usage_event": "typing.test_completed"},
            "generate_certificate": {"required": "typing.certificate_generation", "limit": "typing.certificates_per_month", "period": "month", "usage_event": "typing.certificate_generated"},
            "create_custom_test": {"required": "typing.custom_tests", "period": "none"},
            "view_analytics": {"required": "typing.analytics", "period": "none"},
            "use_premium_lesson": {"required": "typing.premium_tests", "period": "none"},
        },
        "plans": {
            "typing-free": {
                "name": "Typing Free",
                "price_cents": 0,
                "entitlements": {
                    "typing.enabled": True,
                    "typing.tests_per_day": 10,
                    "typing.premium_tests": False,
                    "typing.leaderboard_access": True,
                    "typing.certificate_generation": False,
                    "typing.certificates_per_month": 0,
                    "typing.custom_tests": False,
                    "typing.analytics": False,
                },
            },
            "typing-pro": {
                "name": "Typing Pro",
                "price_cents": 499,
                "entitlements": {
                    "typing.enabled": True,
                    "typing.tests_per_day": 500,
                    "typing.premium_tests": True,
                    "typing.leaderboard_access": True,
                    "typing.certificate_generation": True,
                    "typing.certificates_per_month": 50,
                    "typing.custom_tests": True,
                    "typing.analytics": True,
                },
            },
        },
    },
    "chat": {
        "name": "Chat App",
        "description": "Messages, uploads, rooms, history, and optional AI assistant access.",
        "actions": {
            "send_message": {"required": "chat.enabled", "limit": "chat.messages_per_day", "period": "day", "usage_event": "chat.message_sent"},
            "upload_file": {"required": "chat.file_upload", "limit": "chat.uploads_per_day", "period": "day", "usage_event": "chat.file_uploaded"},
            "create_room": {"required": "chat.enabled", "limit": "chat.group_rooms_limit", "period": "total", "usage_event": "chat.room_created"},
            "use_ai_assistant": {"required": "chat.ai_assistant_access", "period": "none"},
        },
        "plans": {
            "chat-free": {
                "name": "Chat Free",
                "price_cents": 0,
                "entitlements": {
                    "chat.enabled": True,
                    "chat.messages_per_day": 100,
                    "chat.file_upload": False,
                    "chat.uploads_per_day": 0,
                    "chat.attachments_limit_mb": 0,
                    "chat.group_rooms_limit": 2,
                    "chat.history_days": 7,
                    "chat.ai_assistant_access": False,
                },
            },
            "chat-pro": {
                "name": "Chat Pro",
                "price_cents": 999,
                "entitlements": {
                    "chat.enabled": True,
                    "chat.messages_per_day": 5000,
                    "chat.file_upload": True,
                    "chat.uploads_per_day": 100,
                    "chat.attachments_limit_mb": 50,
                    "chat.group_rooms_limit": 50,
                    "chat.history_days": 365,
                    "chat.ai_assistant_access": True,
                },
            },
        },
    },
    "blog": {
        "name": "Blog",
        "description": "Commenting, writing, media upload, SEO tools, and moderation.",
        "actions": {
            "comment": {"required": "blog.can_comment", "period": "none", "usage_event": "blog.comment_created"},
            "write_post": {"required": "blog.can_write_posts", "limit": "blog.posts_per_month", "period": "month", "usage_event": "blog.post_created"},
            "upload_media": {"required": "blog.media_upload", "limit": "blog.media_upload_mb", "period": "month", "usage_event": "blog.media_uploaded_mb"},
            "manage_comments": {"required": "blog.moderation_tools", "period": "none"},
            "use_seo_tools": {"required": "blog.seo_tools", "period": "none"},
        },
        "plans": {
            "blog-free": {
                "name": "Blog Free",
                "price_cents": 0,
                "entitlements": {
                    "blog.enabled": True,
                    "blog.can_comment": True,
                    "blog.can_write_posts": False,
                    "blog.posts_per_month": 0,
                    "blog.media_upload": False,
                    "blog.media_upload_mb": 0,
                    "blog.custom_domain": False,
                    "blog.seo_tools": False,
                    "blog.moderation_tools": False,
                },
            },
            "blog-creator": {
                "name": "Blog Creator",
                "price_cents": 799,
                "entitlements": {
                    "blog.enabled": True,
                    "blog.can_comment": True,
                    "blog.can_write_posts": True,
                    "blog.posts_per_month": 100,
                    "blog.media_upload": True,
                    "blog.media_upload_mb": 1024,
                    "blog.custom_domain": True,
                    "blog.seo_tools": True,
                    "blog.moderation_tools": True,
                },
            },
        },
    },
}


def all_product_codes() -> list[str]:
    return list(BUSINESS_PRODUCTS.keys())


def get_action_rule(product: str, action: str) -> dict | None:
    return BUSINESS_PRODUCTS.get(product, {}).get("actions", {}).get(action)
