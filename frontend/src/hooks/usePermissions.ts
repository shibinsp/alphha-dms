import { useMemo, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'

// Permission definitions matching backend
export type Permission =
  | 'documents:create'
  | 'documents:read'
  | 'documents:update'
  | 'documents:delete'
  | 'documents:approve'
  | 'documents:download'
  | 'documents:share'
  | 'documents:lock'
  | 'documents:legal_hold'
  | 'users:create'
  | 'users:read'
  | 'users:update'
  | 'users:delete'
  | 'users:manage_roles'
  | 'roles:create'
  | 'roles:read'
  | 'roles:update'
  | 'roles:delete'
  | 'audit:read'
  | 'audit:export'
  | 'audit:verify'
  | 'settings:read'
  | 'settings:update'
  | 'pii:view'
  | 'pii:manage'
  | 'analytics:read'
  | 'workflows:create'
  | 'workflows:read'
  | 'workflows:update'
  | 'workflows:delete'
  | 'search:advanced'
  | 'chat:use'
  | 'tenants:manage'

// Clearance levels for document classification
export type ClearanceLevel = 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED'

const CLEARANCE_HIERARCHY: ClearanceLevel[] = ['PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED']

export function usePermissions() {
  const { user } = useAuthStore()

  const userPermissions = useMemo(() => {
    if (!user?.roles) return new Set<string>()

    const permissions = new Set<string>()
    user.roles.forEach((role) => {
      if (role.permissions && Array.isArray(role.permissions)) {
        role.permissions.forEach((perm) => permissions.add(perm))
      }
    })

    return permissions
  }, [user?.roles])

  const userClearance = useMemo((): ClearanceLevel => {
    return (user?.clearance_level as ClearanceLevel) || 'PUBLIC'
  }, [user?.clearance_level])

  const hasPermission = useCallback((permission: Permission | Permission[]): boolean => {
    // Super admin has all permissions
    if (user?.roles?.some((role) => role.name === 'super_admin')) {
      return true
    }

    if (Array.isArray(permission)) {
      return permission.every((p) => userPermissions.has(p))
    }

    return userPermissions.has(permission)
  }, [user?.roles, userPermissions])

  const hasAnyPermission = useCallback((permissions: Permission[]): boolean => {
    // Super admin has all permissions
    if (user?.roles?.some((role) => role.name === 'super_admin')) {
      return true
    }

    return permissions.some((p) => userPermissions.has(p))
  }, [user?.roles, userPermissions])

  const hasClearance = useCallback((requiredLevel: ClearanceLevel): boolean => {
    const userLevel = CLEARANCE_HIERARCHY.indexOf(userClearance)
    const requiredLevelIndex = CLEARANCE_HIERARCHY.indexOf(requiredLevel)
    return userLevel >= requiredLevelIndex
  }, [userClearance])

  const hasRole = useCallback((roleName: string | string[]): boolean => {
    if (!user?.roles) return false

    if (Array.isArray(roleName)) {
      return roleName.some((name) => user.roles?.some((role) => role.name === name))
    }

    return user.roles.some((role) => role.name === roleName)
  }, [user?.roles])

  const isAdmin = useMemo(() => {
    return hasRole(['super_admin', 'admin'])
  }, [hasRole])

  const isSuperAdmin = useMemo(() => {
    return hasRole('super_admin')
  }, [hasRole])

  const canAccessDocument = useCallback((documentClassification: ClearanceLevel): boolean => {
    return hasClearance(documentClassification) && hasPermission('documents:read')
  }, [hasClearance, hasPermission])

  const canEditDocument = useCallback((documentClassification: ClearanceLevel, isLocked: boolean, isLegalHold: boolean): boolean => {
    if (isLocked || isLegalHold) return false
    return hasClearance(documentClassification) && hasPermission('documents:update')
  }, [hasClearance, hasPermission])

  const canDeleteDocument = useCallback((documentClassification: ClearanceLevel, isLocked: boolean, isLegalHold: boolean): boolean => {
    if (isLocked || isLegalHold) return false
    return hasClearance(documentClassification) && hasPermission('documents:delete')
  }, [hasClearance, hasPermission])

  return {
    permissions: userPermissions,
    clearanceLevel: userClearance,
    hasPermission,
    hasAnyPermission,
    hasClearance,
    hasRole,
    isAdmin,
    isSuperAdmin,
    canAccessDocument,
    canEditDocument,
    canDeleteDocument,
  }
}
