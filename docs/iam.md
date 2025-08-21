# IAM (Identity and Access Management) Documentation

## 1. Permissions Overview

In the Identity and Access Management (IAM) system, a **Permission** is a fundamental concept that defines the right to perform a specific action on a specific resource within the system. IAM operates on a **"deny by default" model** — this means that if a user or service does not have an explicitly granted permission for an action, that action will be blocked.

### 1.1. Permission Structure

Each permission is represented as a string consisting of three parts separated by dots:

`<service_name>.<resource_name>.<action>`

*   **`<service_name>`**:
    *   A unique identifier for a service or module in your system
    *   Examples: `billing`, `compute`, `auth`, `storage`

*   **`<resource_name>`**:
    *   Defines the type of object an action can be performed on
    *   Expressed in the **singular form**
    *   Examples: `account`, `vm`, `user`, `policy`

*   **`<action>`**:
    *   Defines the operation that can be performed on the specified resource
    *   Examples: `read`, `write`, `create`, `delete`, `activate`

**Permission examples:**
*   `billing.account.read` — view account information in the billing service
*   `compute.vm.create` — create a new virtual machine in the compute service
*   `auth.user.deactivate` — deactivate a user in the authentication service

### 1.2. Security Model: "Deny by Default"

An important IAM philosophy is the principle of **explicit permission**:
*   Initially, any user or service account has no access rights
*   To perform any action, the subject must be granted the corresponding permission
*   Services integrated with IAM must check for the required permission before executing an operation

### 1.3. Permissions API Examples

#### Create a Permission
```http
POST /v1/iam/permissions/
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "compute.vm.create",
  "description": "Permission to create a virtual machine"
}
```

#### Response
```json
{
  "uuid": "5a1b2c3d-4e5f-6789-abcd-ef0123456789",
  "name": "compute.vm.create",
  "description": "Permission to create a virtual machine",
  "created_at": "2025-08-21T07:38:04.778680Z",
  "updated_at": "2025-08-21T07:38:04.778688Z",
  "status": "ACTIVE"
}
```

#### Get a Permission
```http
GET /v1/iam/permissions/5a1b2c3d-4e5f-6789-abcd-ef0123456789
Authorization: Bearer <token>
```

#### Filter Permissions
```http
GET /v1/iam/permissions/?name=compute.vm.&status=ACTIVE
Authorization: Bearer <token>
```

## 2. Roles

A **Role** is a named collection of Permissions. While a Permission defines the right for one specific action, a Role groups these rights into logical blocks corresponding to job functions, responsibilities, or the access level of a user or service.

### 2.1. Permission Binding: Linking Roles and Permissions

To assign permissions to a role, the **Permission Binding** entity is used. This entity establishes a many-to-many relationship between roles and permissions.

*   **One Permission** can be bound to **several different roles**
*   **One Role** can contain **many different permissions**

**Example:**
*   The `BillingViewer` role receives the following via Permission Binding:
    *   `billing.account.read`
    *   `billing.invoice.read`
*   The `BillingOperator` role receives the following via Permission Binding:
    *   `billing.account.read`
    *   `billing.invoice.read`
    *   `billing.invoice.pay`

### 2.2. Role Binding: Assigning Roles to Users

To grant a user access, a role must be assigned to them. The **Role Binding** entity is used for this purpose. This entity establishes a many-to-many relationship between users and roles.

*   **One user** can be assigned **several roles**
*   **One role** can be assigned to **many users**

### 2.3. Final Access Model

The access verification process:
1.  A **User** makes a request to a service
2.  The **Service** determines which permission is needed for this action
3.  **IAM** checks:
    *   Which **roles** are assigned to the user (via all their Role Bindings)
    *   Which **permissions** are included in these roles (via all Permission Bindings for these roles)
4.  If at least one of the user's roles contains the required permission, access is **granted**

### 2.4. Roles API Examples

#### Create a Role
```http
POST /v1/iam/roles/
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "BillingOperator",
  "description": "Billing operator with rights to manage accounts"
}
```

#### Response
```json
{
  "uuid": "6b2c3d4e-5f67-789a-bcde-f01234567890",
  "name": "BillingOperator",
  "description": "Billing operator with rights to manage accounts",
  "created_at": "2025-08-21T07:38:04.779416Z",
  "updated_at": "2025-08-21T07:38:04.779424Z",
  "status": "ACTIVE",
  "project_id": null
}
```

#### Create a Permission Binding
```http
POST /v1/iam/permission_bindings/
Content-Type: application/json
Authorization: Bearer <token>

{
  "role": "6b2c3d4e-5f67-789a-bcde-f01234567890",
  "permission": "5a1b2c3d-4e5f-6789-abcd-ef0123456789"
}
```

#### Create a Role Binding
```http
POST /v1/iam/role_bindings/
Content-Type: application/json
Authorization: Bearer <token>

{
  "user": "7c3d4e5f-6789-89ab-cdef-123456789012",
  "role": "6b2c3d4e-5f67-789a-bcde-f01234567890",
  "project": "8d4e5f67-789a-9abc-def1-234567890123"
}
```

#### Get User Roles
```http
GET /v1/iam/users/7c3d4e5f-6789-89ab-cdef-123456789012/actions/get_my_roles
Authorization: Bearer <token>
```

## 3. Best Practices

### 3.1. Principle of Least Privilege
Create roles that provide exactly the level of access required to perform a task, and nothing more.

### 3.2. Semantic Naming
Give roles and permissions clear names that reflect their purpose:
*   Roles: `NetworkReadOnly`, `DatabaseSuperUser`
*   Permissions: `compute.vm.read`, `storage.bucket.delete`

### 3.3. Regular Audits
Periodically review:
*   Which roles are assigned to whom
*   Which permissions are included in roles
*   Remove unnecessary access promptly

### 3.4. Using Projects for Isolation
Assign roles within the context of specific projects to ensure environment isolation:
```json
{
  "user": "7c3d4e5f-6789-89ab-cdef-123456789012",
  "role": "6b2c3d4e-5f67-789a-bcde-f01234567890",
  "project": "8d4e5f67-789a-9abc-def1-234567890123"
}
```

## 4. Error Handling

The following errors may occur when working with the IAM API:

### 4.1. Access Error (403 Forbidden)
```json
{
  "status": 403,
  "json": {
    "code": 403,
    "type": "PermissionDeniedException",
    "message": "User does not have required permission: compute.vm.create"
  }
}
```

### 4.2. Not Found (404 Not Found)
```json
{
  "status": 404,
  "json": {
    "code": 404,
    "type": "NotFoundException",
    "message": "Role with uuid 6b2c3d4e-5f67-789a-bcde-f01234567890 not found"
  }
}
```

### 4.3. Bad Request (400 Bad Request)
```json
{
  "status": 400,
  "json": {
    "code": 400,
    "type": "ValidationErrorException",
    "message": "Field 'name' must be between 0 and 255 characters"
  }
}
```

## 5. Important Notes

1.  All changes to permissions and role bindings take effect immediately
2.  Caching access rights on the client side is not recommended
3.  For service accounts, use separate roles with the minimum required permissions
4.  Regularly update and review role assignments within the system

This documentation covers the basic aspects of working with the IAM system in Genesis Core. For more detailed information about specific API endpoints, refer to the full OpenAPI specification.
