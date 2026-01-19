#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_6080834398693620578) {
   out_6080834398693620578[0] = delta_x[0] + nom_x[0];
   out_6080834398693620578[1] = delta_x[1] + nom_x[1];
   out_6080834398693620578[2] = delta_x[2] + nom_x[2];
   out_6080834398693620578[3] = delta_x[3] + nom_x[3];
   out_6080834398693620578[4] = delta_x[4] + nom_x[4];
   out_6080834398693620578[5] = delta_x[5] + nom_x[5];
   out_6080834398693620578[6] = delta_x[6] + nom_x[6];
   out_6080834398693620578[7] = delta_x[7] + nom_x[7];
   out_6080834398693620578[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1157127680835189021) {
   out_1157127680835189021[0] = -nom_x[0] + true_x[0];
   out_1157127680835189021[1] = -nom_x[1] + true_x[1];
   out_1157127680835189021[2] = -nom_x[2] + true_x[2];
   out_1157127680835189021[3] = -nom_x[3] + true_x[3];
   out_1157127680835189021[4] = -nom_x[4] + true_x[4];
   out_1157127680835189021[5] = -nom_x[5] + true_x[5];
   out_1157127680835189021[6] = -nom_x[6] + true_x[6];
   out_1157127680835189021[7] = -nom_x[7] + true_x[7];
   out_1157127680835189021[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6798648444481860721) {
   out_6798648444481860721[0] = 1.0;
   out_6798648444481860721[1] = 0.0;
   out_6798648444481860721[2] = 0.0;
   out_6798648444481860721[3] = 0.0;
   out_6798648444481860721[4] = 0.0;
   out_6798648444481860721[5] = 0.0;
   out_6798648444481860721[6] = 0.0;
   out_6798648444481860721[7] = 0.0;
   out_6798648444481860721[8] = 0.0;
   out_6798648444481860721[9] = 0.0;
   out_6798648444481860721[10] = 1.0;
   out_6798648444481860721[11] = 0.0;
   out_6798648444481860721[12] = 0.0;
   out_6798648444481860721[13] = 0.0;
   out_6798648444481860721[14] = 0.0;
   out_6798648444481860721[15] = 0.0;
   out_6798648444481860721[16] = 0.0;
   out_6798648444481860721[17] = 0.0;
   out_6798648444481860721[18] = 0.0;
   out_6798648444481860721[19] = 0.0;
   out_6798648444481860721[20] = 1.0;
   out_6798648444481860721[21] = 0.0;
   out_6798648444481860721[22] = 0.0;
   out_6798648444481860721[23] = 0.0;
   out_6798648444481860721[24] = 0.0;
   out_6798648444481860721[25] = 0.0;
   out_6798648444481860721[26] = 0.0;
   out_6798648444481860721[27] = 0.0;
   out_6798648444481860721[28] = 0.0;
   out_6798648444481860721[29] = 0.0;
   out_6798648444481860721[30] = 1.0;
   out_6798648444481860721[31] = 0.0;
   out_6798648444481860721[32] = 0.0;
   out_6798648444481860721[33] = 0.0;
   out_6798648444481860721[34] = 0.0;
   out_6798648444481860721[35] = 0.0;
   out_6798648444481860721[36] = 0.0;
   out_6798648444481860721[37] = 0.0;
   out_6798648444481860721[38] = 0.0;
   out_6798648444481860721[39] = 0.0;
   out_6798648444481860721[40] = 1.0;
   out_6798648444481860721[41] = 0.0;
   out_6798648444481860721[42] = 0.0;
   out_6798648444481860721[43] = 0.0;
   out_6798648444481860721[44] = 0.0;
   out_6798648444481860721[45] = 0.0;
   out_6798648444481860721[46] = 0.0;
   out_6798648444481860721[47] = 0.0;
   out_6798648444481860721[48] = 0.0;
   out_6798648444481860721[49] = 0.0;
   out_6798648444481860721[50] = 1.0;
   out_6798648444481860721[51] = 0.0;
   out_6798648444481860721[52] = 0.0;
   out_6798648444481860721[53] = 0.0;
   out_6798648444481860721[54] = 0.0;
   out_6798648444481860721[55] = 0.0;
   out_6798648444481860721[56] = 0.0;
   out_6798648444481860721[57] = 0.0;
   out_6798648444481860721[58] = 0.0;
   out_6798648444481860721[59] = 0.0;
   out_6798648444481860721[60] = 1.0;
   out_6798648444481860721[61] = 0.0;
   out_6798648444481860721[62] = 0.0;
   out_6798648444481860721[63] = 0.0;
   out_6798648444481860721[64] = 0.0;
   out_6798648444481860721[65] = 0.0;
   out_6798648444481860721[66] = 0.0;
   out_6798648444481860721[67] = 0.0;
   out_6798648444481860721[68] = 0.0;
   out_6798648444481860721[69] = 0.0;
   out_6798648444481860721[70] = 1.0;
   out_6798648444481860721[71] = 0.0;
   out_6798648444481860721[72] = 0.0;
   out_6798648444481860721[73] = 0.0;
   out_6798648444481860721[74] = 0.0;
   out_6798648444481860721[75] = 0.0;
   out_6798648444481860721[76] = 0.0;
   out_6798648444481860721[77] = 0.0;
   out_6798648444481860721[78] = 0.0;
   out_6798648444481860721[79] = 0.0;
   out_6798648444481860721[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2949828160148673620) {
   out_2949828160148673620[0] = state[0];
   out_2949828160148673620[1] = state[1];
   out_2949828160148673620[2] = state[2];
   out_2949828160148673620[3] = state[3];
   out_2949828160148673620[4] = state[4];
   out_2949828160148673620[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8000000000000007*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2949828160148673620[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2949828160148673620[7] = state[7];
   out_2949828160148673620[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3046190426194535579) {
   out_3046190426194535579[0] = 1;
   out_3046190426194535579[1] = 0;
   out_3046190426194535579[2] = 0;
   out_3046190426194535579[3] = 0;
   out_3046190426194535579[4] = 0;
   out_3046190426194535579[5] = 0;
   out_3046190426194535579[6] = 0;
   out_3046190426194535579[7] = 0;
   out_3046190426194535579[8] = 0;
   out_3046190426194535579[9] = 0;
   out_3046190426194535579[10] = 1;
   out_3046190426194535579[11] = 0;
   out_3046190426194535579[12] = 0;
   out_3046190426194535579[13] = 0;
   out_3046190426194535579[14] = 0;
   out_3046190426194535579[15] = 0;
   out_3046190426194535579[16] = 0;
   out_3046190426194535579[17] = 0;
   out_3046190426194535579[18] = 0;
   out_3046190426194535579[19] = 0;
   out_3046190426194535579[20] = 1;
   out_3046190426194535579[21] = 0;
   out_3046190426194535579[22] = 0;
   out_3046190426194535579[23] = 0;
   out_3046190426194535579[24] = 0;
   out_3046190426194535579[25] = 0;
   out_3046190426194535579[26] = 0;
   out_3046190426194535579[27] = 0;
   out_3046190426194535579[28] = 0;
   out_3046190426194535579[29] = 0;
   out_3046190426194535579[30] = 1;
   out_3046190426194535579[31] = 0;
   out_3046190426194535579[32] = 0;
   out_3046190426194535579[33] = 0;
   out_3046190426194535579[34] = 0;
   out_3046190426194535579[35] = 0;
   out_3046190426194535579[36] = 0;
   out_3046190426194535579[37] = 0;
   out_3046190426194535579[38] = 0;
   out_3046190426194535579[39] = 0;
   out_3046190426194535579[40] = 1;
   out_3046190426194535579[41] = 0;
   out_3046190426194535579[42] = 0;
   out_3046190426194535579[43] = 0;
   out_3046190426194535579[44] = 0;
   out_3046190426194535579[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3046190426194535579[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3046190426194535579[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3046190426194535579[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3046190426194535579[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3046190426194535579[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3046190426194535579[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3046190426194535579[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3046190426194535579[53] = -9.8000000000000007*dt;
   out_3046190426194535579[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3046190426194535579[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3046190426194535579[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3046190426194535579[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3046190426194535579[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3046190426194535579[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3046190426194535579[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3046190426194535579[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3046190426194535579[62] = 0;
   out_3046190426194535579[63] = 0;
   out_3046190426194535579[64] = 0;
   out_3046190426194535579[65] = 0;
   out_3046190426194535579[66] = 0;
   out_3046190426194535579[67] = 0;
   out_3046190426194535579[68] = 0;
   out_3046190426194535579[69] = 0;
   out_3046190426194535579[70] = 1;
   out_3046190426194535579[71] = 0;
   out_3046190426194535579[72] = 0;
   out_3046190426194535579[73] = 0;
   out_3046190426194535579[74] = 0;
   out_3046190426194535579[75] = 0;
   out_3046190426194535579[76] = 0;
   out_3046190426194535579[77] = 0;
   out_3046190426194535579[78] = 0;
   out_3046190426194535579[79] = 0;
   out_3046190426194535579[80] = 1;
}
void h_25(double *state, double *unused, double *out_1901206799855987806) {
   out_1901206799855987806[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4162091519466434527) {
   out_4162091519466434527[0] = 0;
   out_4162091519466434527[1] = 0;
   out_4162091519466434527[2] = 0;
   out_4162091519466434527[3] = 0;
   out_4162091519466434527[4] = 0;
   out_4162091519466434527[5] = 0;
   out_4162091519466434527[6] = 1;
   out_4162091519466434527[7] = 0;
   out_4162091519466434527[8] = 0;
}
void h_24(double *state, double *unused, double *out_1632654478212159168) {
   out_1632654478212159168[0] = state[4];
   out_1632654478212159168[1] = state[5];
}
void H_24(double *state, double *unused, double *out_4567189380435876082) {
   out_4567189380435876082[0] = 0;
   out_4567189380435876082[1] = 0;
   out_4567189380435876082[2] = 0;
   out_4567189380435876082[3] = 0;
   out_4567189380435876082[4] = 1;
   out_4567189380435876082[5] = 0;
   out_4567189380435876082[6] = 0;
   out_4567189380435876082[7] = 0;
   out_4567189380435876082[8] = 0;
   out_4567189380435876082[9] = 0;
   out_4567189380435876082[10] = 0;
   out_4567189380435876082[11] = 0;
   out_4567189380435876082[12] = 0;
   out_4567189380435876082[13] = 0;
   out_4567189380435876082[14] = 1;
   out_4567189380435876082[15] = 0;
   out_4567189380435876082[16] = 0;
   out_4567189380435876082[17] = 0;
}
void h_30(double *state, double *unused, double *out_8672042026206338742) {
   out_8672042026206338742[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6680424477973683154) {
   out_6680424477973683154[0] = 0;
   out_6680424477973683154[1] = 0;
   out_6680424477973683154[2] = 0;
   out_6680424477973683154[3] = 0;
   out_6680424477973683154[4] = 1;
   out_6680424477973683154[5] = 0;
   out_6680424477973683154[6] = 0;
   out_6680424477973683154[7] = 0;
   out_6680424477973683154[8] = 0;
}
void h_26(double *state, double *unused, double *out_9171386162826735357) {
   out_9171386162826735357[0] = state[7];
}
void H_26(double *state, double *unused, double *out_420588200592378303) {
   out_420588200592378303[0] = 0;
   out_420588200592378303[1] = 0;
   out_420588200592378303[2] = 0;
   out_420588200592378303[3] = 0;
   out_420588200592378303[4] = 0;
   out_420588200592378303[5] = 0;
   out_420588200592378303[6] = 0;
   out_420588200592378303[7] = 1;
   out_420588200592378303[8] = 0;
}
void h_27(double *state, double *unused, double *out_8364114402383816459) {
   out_8364114402383816459[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4505661166173258243) {
   out_4505661166173258243[0] = 0;
   out_4505661166173258243[1] = 0;
   out_4505661166173258243[2] = 0;
   out_4505661166173258243[3] = 1;
   out_4505661166173258243[4] = 0;
   out_4505661166173258243[5] = 0;
   out_4505661166173258243[6] = 0;
   out_4505661166173258243[7] = 0;
   out_4505661166173258243[8] = 0;
}
void h_29(double *state, double *unused, double *out_6962149944233359491) {
   out_6962149944233359491[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7190655822288075338) {
   out_7190655822288075338[0] = 0;
   out_7190655822288075338[1] = 1;
   out_7190655822288075338[2] = 0;
   out_7190655822288075338[3] = 0;
   out_7190655822288075338[4] = 0;
   out_7190655822288075338[5] = 0;
   out_7190655822288075338[6] = 0;
   out_7190655822288075338[7] = 0;
   out_7190655822288075338[8] = 0;
}
void h_28(double *state, double *unused, double *out_2156956614903195404) {
   out_2156956614903195404[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2108256805218544764) {
   out_2108256805218544764[0] = 1;
   out_2108256805218544764[1] = 0;
   out_2108256805218544764[2] = 0;
   out_2108256805218544764[3] = 0;
   out_2108256805218544764[4] = 0;
   out_2108256805218544764[5] = 0;
   out_2108256805218544764[6] = 0;
   out_2108256805218544764[7] = 0;
   out_2108256805218544764[8] = 0;
}
void h_31(double *state, double *unused, double *out_499242341705530838) {
   out_499242341705530838[0] = state[8];
}
void H_31(double *state, double *unused, double *out_205619901640973173) {
   out_205619901640973173[0] = 0;
   out_205619901640973173[1] = 0;
   out_205619901640973173[2] = 0;
   out_205619901640973173[3] = 0;
   out_205619901640973173[4] = 0;
   out_205619901640973173[5] = 0;
   out_205619901640973173[6] = 0;
   out_205619901640973173[7] = 0;
   out_205619901640973173[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_6080834398693620578) {
  err_fun(nom_x, delta_x, out_6080834398693620578);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1157127680835189021) {
  inv_err_fun(nom_x, true_x, out_1157127680835189021);
}
void car_H_mod_fun(double *state, double *out_6798648444481860721) {
  H_mod_fun(state, out_6798648444481860721);
}
void car_f_fun(double *state, double dt, double *out_2949828160148673620) {
  f_fun(state,  dt, out_2949828160148673620);
}
void car_F_fun(double *state, double dt, double *out_3046190426194535579) {
  F_fun(state,  dt, out_3046190426194535579);
}
void car_h_25(double *state, double *unused, double *out_1901206799855987806) {
  h_25(state, unused, out_1901206799855987806);
}
void car_H_25(double *state, double *unused, double *out_4162091519466434527) {
  H_25(state, unused, out_4162091519466434527);
}
void car_h_24(double *state, double *unused, double *out_1632654478212159168) {
  h_24(state, unused, out_1632654478212159168);
}
void car_H_24(double *state, double *unused, double *out_4567189380435876082) {
  H_24(state, unused, out_4567189380435876082);
}
void car_h_30(double *state, double *unused, double *out_8672042026206338742) {
  h_30(state, unused, out_8672042026206338742);
}
void car_H_30(double *state, double *unused, double *out_6680424477973683154) {
  H_30(state, unused, out_6680424477973683154);
}
void car_h_26(double *state, double *unused, double *out_9171386162826735357) {
  h_26(state, unused, out_9171386162826735357);
}
void car_H_26(double *state, double *unused, double *out_420588200592378303) {
  H_26(state, unused, out_420588200592378303);
}
void car_h_27(double *state, double *unused, double *out_8364114402383816459) {
  h_27(state, unused, out_8364114402383816459);
}
void car_H_27(double *state, double *unused, double *out_4505661166173258243) {
  H_27(state, unused, out_4505661166173258243);
}
void car_h_29(double *state, double *unused, double *out_6962149944233359491) {
  h_29(state, unused, out_6962149944233359491);
}
void car_H_29(double *state, double *unused, double *out_7190655822288075338) {
  H_29(state, unused, out_7190655822288075338);
}
void car_h_28(double *state, double *unused, double *out_2156956614903195404) {
  h_28(state, unused, out_2156956614903195404);
}
void car_H_28(double *state, double *unused, double *out_2108256805218544764) {
  H_28(state, unused, out_2108256805218544764);
}
void car_h_31(double *state, double *unused, double *out_499242341705530838) {
  h_31(state, unused, out_499242341705530838);
}
void car_H_31(double *state, double *unused, double *out_205619901640973173) {
  H_31(state, unused, out_205619901640973173);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
