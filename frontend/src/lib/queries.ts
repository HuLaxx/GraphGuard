import { gql } from "@apollo/client";

export const GET_DASHBOARD_DATA = gql`
  query GetDashboardData {
    dashboardMetrics {
      totalTransactions
      fraudRate
      autoApproved
      autoDeclined
      pendingReview
      avgLatencyMs
      p99LatencyMs
      modelAccuracy
    }
    fraudQueue(limit: 20, status: PENDING) {
      items {
        id
        transactionId
        userId
        merchantName
        amountVal
        currencyCode
        fraudScore
        priority
        status
        createdAt
      }
      totalCount
    }
  }
`;

export const GET_CASE_DETAILS = gql`
  query GetCaseDetails($id: ID!) {
    fraudCase(id: $id) {
      id
      transactionId
      userId
      amountVal
      currencyCode
      fraudScore
      status
      priority
      createdAt
      transaction {
        id
        amount
        timestamp
        decision
      }
    }
  }
`;

export const GET_SUSPICIOUS_SUBGRAPH = gql`
  query GetSuspiciousSubgraph($userId: ID!, $hops: Int) {
    suspiciousSubgraph(userId: $userId, hops: $hops) {
      nodes {
        id
        type
        label
        riskScore
        isFlagged
      }
      edges {
        source
        target
        type
        amount
      }
    }
  }
`;

export const GET_SHAP_EXPLANATION = gql`
  query GetShapExplanation($transactionId: ID!) {
    shapExplanation(transactionId: $transactionId) {
      baseValue
      predictionValue
      plainEnglish
      features {
        name
        value
        shapValue
        importance
        impact
        description
      }
    }
  }
`;

export const LABEL_CASE_MUTATION = gql`
  mutation LabelCase($id: ID!, $label: FraudLabel!, $notes: String) {
    labelCase(id: $id, label: $label, notes: $notes) {
      id
      status
    }
  }
`;
