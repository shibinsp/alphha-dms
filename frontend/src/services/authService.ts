import api from './api'
import type { User, TokenResponse, LoginRequest } from '@/types'

export const authService = {
  async login(credentials: LoginRequest): Promise<{ user: User; tokens: TokenResponse }> {
    // Login to get tokens
    const tokenResponse = await api.post<TokenResponse>('/auth/login/json', credentials)
    const tokens = tokenResponse.data

    // Get user info
    api.defaults.headers.common.Authorization = `Bearer ${tokens.access_token}`
    const userResponse = await api.get<User>('/auth/me')

    return {
      user: userResponse.data,
      tokens,
    }
  },

  async logout(refreshToken: string): Promise<void> {
    await api.post('/auth/logout', { refresh_token: refreshToken })
  },

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me')
    return response.data
  },

  async setupMFA(): Promise<{ secret: string; qr_code: string }> {
    const response = await api.post<{ secret: string; qr_code: string }>('/auth/mfa/setup')
    return response.data
  },

  async verifyMFA(secret: string, code: string): Promise<void> {
    await api.post('/auth/mfa/verify', { code, secret })
  },

  async disableMFA(code: string): Promise<void> {
    await api.delete('/auth/mfa', { data: { code } })
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/password/change', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },
}
