# Release Notes - v43 Business Core

## Purpose

v43 refocuses the project for the real business scope: central authentication and payment processing for the ZATCA document generator, typing test, chat app, and blog.

## Changes

- Added `config/app_registry.py` to separate required business apps from optional advanced apps.
- Changed the default runtime profile to `business`.
- Disabled advanced enterprise/compliance/usage/tax modules by default.
- Made URL registration dynamic so disabled apps are not imported or exposed.
- Added product/entitlement catalog for the four business apps.
- Added `seed_business_products` management command.
- Added Makefile helpers for business-core checks and seed data.
- Added business-focused deployment documentation.
- Updated API version metadata to `43.0.0`.

## Required launch apps

- accounts
- billing
- admin_integration
- admin_console
- customer_portal
- notifications
- ops
- production_verification

## Compatibility with Admin Control Platform

v43 keeps the admin integration API and admin console API enabled by default so the separate Admin Control Platform can manage users, plans, subscriptions, custom/free access, and product entitlements through APIs.

## Important note

Advanced app directories remain in the repository for future upgrades, but they are no longer part of the default production runtime.
