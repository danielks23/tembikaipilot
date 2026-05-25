#include "selfdrive/ui/qt/body.h"
#include <QLabel>
#include <QVBoxLayout>

BodyWindow::BodyWindow(QWidget* parent) : QWidget(parent) {
  QVBoxLayout *layout = new QVBoxLayout(this);
  layout->addWidget(new QLabel("Body teleop not available"));
}
